# Copyright 2024 Kencove Farm Fence Supplies
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64
import hashlib
import hmac
import json
import logging
import threading
import time
from datetime import datetime

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

# In-memory dedup cache: {dedup_key: timestamp}.
# Prevents redundant processing when Onshape fires the same event
# multiple times within a short window (common with per-document webhooks).
# Protected by _DEDUP_LOCK because concurrent threads can race on
# the read-check-write sequence.
_RECENT_EVENTS = {}
_DEDUP_LOCK = threading.Lock()
_DEDUP_WINDOW = 5  # seconds


class OnshapeWebhookController(http.Controller):
    """Receive Onshape webhook events.

    Route: /connector_onshape/webhook/<backend_id>

    Events handled:
    - onshape.model.lifecycle.metadata → re-import part metadata
    - onshape.workflow.transition → update lifecycle state
    - onshape.revision.created → mark as released
    - onshape.model.lifecycle.createversion → log version creation

    Security: Validate HMAC signature, then re-fetch from API
    (never trust webhook payload directly).
    """

    @http.route(
        "/connector_onshape/webhook/<int:backend_id>",
        type="json",
        auth="none",
        methods=["POST"],
        csrf=False,
    )
    def webhook(self, backend_id, **kwargs):
        backend = request.env["onshape.backend"].sudo().browse(backend_id).exists()
        if not backend:
            _logger.warning("Webhook received for unknown backend %s", backend_id)
            return {"status": "error", "message": "Unknown backend"}

        # Validate HMAC signature when available.
        # Enterprise plans: Onshape signs payloads with keys configured in
        # the company admin panel. The webhook_secret field should match
        # the primary or secondary key from Onshape's settings.
        # EDU/Free plans: Onshape may not send signature headers.
        raw_body = request.httprequest.get_data()
        signature = request.httprequest.headers.get(
            "X-onshape-webhook-signature-primary", ""
        )
        timestamp = request.httprequest.headers.get("X-onshape-webhook-timestamp", "")
        if signature:
            if not backend.webhook_secret:
                _logger.warning(
                    "Webhook has signature but no secret configured "
                    "for backend %s. Rejecting.",
                    backend_id,
                )
                return {"status": "error", "message": "Webhook secret not configured"}
            if not self._validate_signature(
                raw_body, backend.webhook_secret, signature, timestamp
            ):
                _logger.warning(
                    "Webhook signature validation failed for backend %s",
                    backend_id,
                )
                return {"status": "error", "message": "Invalid signature"}
        else:
            _logger.debug(
                "No signature header on webhook for backend %s — "
                "skipping HMAC validation (EDU/Free plan).",
                backend_id,
            )

        try:
            payload = json.loads(raw_body)
        except (json.JSONDecodeError, TypeError):
            return {"status": "error", "message": "Invalid JSON"}

        event = payload.get("event", "")
        _logger.info(
            "Onshape webhook received: event=%s backend=%s",
            event,
            backend_id,
        )

        # Deduplicate rapid-fire identical events (webhookId excluded).
        doc_id = payload.get("documentId", "")
        dedup_key = (
            backend_id,
            event,
            doc_id,
            payload.get("versionName", ""),
            payload.get("transitionName", ""),
            payload.get("elementId", ""),
            payload.get("partId", ""),
        )
        now = time.monotonic()
        with _DEDUP_LOCK:
            last_seen = _RECENT_EVENTS.get(dedup_key, 0)
            if now - last_seen < _DEDUP_WINDOW:
                _logger.info(
                    "Skipping duplicate webhook: event=%s doc=%s (%.1fs ago)",
                    event,
                    doc_id,
                    now - last_seen,
                )
                return {"status": "ok", "message": "Duplicate suppressed"}
            _RECENT_EVENTS[dedup_key] = now
            # Prune stale entries to avoid unbounded growth
            if len(_RECENT_EVENTS) > 500:
                cutoff = now - _DEDUP_WINDOW
                stale = [k for k, v in _RECENT_EVENTS.items() if v < cutoff]
                for k in stale:
                    del _RECENT_EVENTS[k]

        # Dispatch by event type
        handler = self._get_event_handler(event)
        if handler:
            handler(backend, payload)
            return {"status": "ok"}

        _logger.debug("Unhandled webhook event: %s", event)
        return {"status": "ok", "message": "Event not handled"}

    def _validate_signature(self, raw_body, secret, signature, timestamp=""):
        """Validate Onshape webhook HMAC-SHA256 signature.

        Onshape signs ``timestamp + "." + raw_body`` and sends the result
        as a Base64-encoded HMAC-SHA256 digest.
        """
        message = timestamp.encode("utf-8") + b"." + raw_body if timestamp else raw_body
        expected = base64.b64encode(
            hmac.new(
                secret.encode("utf-8"),
                message,
                digestmod=hashlib.sha256,
            ).digest()
        ).decode("ascii")
        return hmac.compare_digest(expected, signature)

    def _get_event_handler(self, event):
        handlers = {
            "onshape.model.lifecycle.metadata": self._handle_metadata_change,
            "onshape.workflow.transition": self._handle_workflow_transition,
            "onshape.revision.created": self._handle_revision_created,
            "onshape.model.lifecycle.createversion": (self._handle_version_created),
            "webhook.unregister": self._handle_webhook_unregister,
        }
        return handlers.get(event)

    def _handle_metadata_change(self, backend, payload):
        """Re-import part metadata when it changes in Onshape.

        Queues a document-scoped re-import (not full backend resync)
        so we pull fresh data from the Onshape API.
        """
        doc_id = payload.get("documentId", "")
        if not doc_id:
            return

        document = (
            request.env["onshape.document"]
            .sudo()
            .search(
                [
                    ("backend_id", "=", backend.id),
                    ("onshape_document_id", "=", doc_id),
                ],
                limit=1,
            )
        )
        if not document:
            _logger.debug("Webhook metadata change for unknown doc %s", doc_id)
            return

        # Sync document name/timestamps
        self._sync_document(backend, doc_id)

        # Queue document-scoped product re-import (not full backend resync)
        backend.with_delay(
            priority=10,
            description=f"Re-import products for doc {document.name}",
        ).action_import_products_for_document(document)

    def _handle_workflow_transition(self, backend, payload):
        """Update lifecycle state when workflow transitions."""
        doc_id = payload.get("documentId", "")
        new_state = (payload.get("transitionName") or "").lower()

        state_map = {
            "release": "released",
            "obsolete": "obsolete",
            "in progress": "in_progress",
            "pending": "pending",
        }
        mapped_state = state_map.get(new_state)
        if not mapped_state:
            return

        bindings = self._find_bindings(backend, payload)
        if bindings:
            bindings.write({"onshape_state": mapped_state})
            _logger.info(
                "Updated %d bindings to state %s for doc %s",
                len(bindings),
                mapped_state,
                doc_id,
            )

    def _handle_revision_created(self, backend, payload):
        """Mark parts as released when a revision is created."""
        bindings = self._find_bindings(backend, payload)
        if bindings:
            bindings.write({"onshape_state": "released"})

    def _find_bindings(self, backend, payload):
        """Find product bindings matching the webhook payload scope."""
        doc_id = payload.get("documentId", "")
        elem_id = payload.get("elementId", "")
        part_id = payload.get("partId", "")
        domain = [
            ("backend_id", "=", backend.id),
            ("onshape_document_id.onshape_document_id", "=", doc_id),
        ]
        if elem_id:
            domain.append(("onshape_element_id", "=", elem_id))
        if part_id:
            domain.append(("onshape_part_id", "=", part_id))
        return request.env["onshape.product.product"].sudo().search(domain)

    def _handle_version_created(self, backend, payload):
        """Sync document on version creation."""
        doc_id = payload.get("documentId", "")
        version_name = payload.get("versionName", "")
        _logger.info(
            "Onshape version created: doc=%s version=%s",
            doc_id,
            version_name,
        )
        self._sync_document(backend, doc_id)

    def _handle_webhook_unregister(self, backend, payload):
        """Clear webhook tracking when Onshape expires/unregisters a webhook.

        Onshape sends this event when a transient webhook expires or is
        manually deleted. We look up the document by stored webhook ID
        and clear the field so the next "Register Webhook" run re-creates it.
        """
        webhook_id = payload.get("webhookId", "")
        if not webhook_id:
            return
        document = (
            request.env["onshape.document"]
            .sudo()
            .search(
                [
                    ("backend_id", "=", backend.id),
                    ("onshape_webhook_id", "=", webhook_id),
                ],
                limit=1,
            )
        )
        if document:
            document.write({"onshape_webhook_id": False})
            _logger.info(
                "Webhook %s expired/unregistered — cleared from document %s (%s)",
                webhook_id,
                document.name,
                document.onshape_document_id,
            )
        else:
            _logger.debug(
                "webhook.unregister for unknown webhook ID %s on backend %s",
                webhook_id,
                backend.id,
            )

    def _sync_document(self, backend, doc_id):
        """Re-fetch document data from Onshape and update local record."""
        if not doc_id:
            return
        document = (
            request.env["onshape.document"]
            .sudo()
            .search(
                [
                    ("backend_id", "=", backend.id),
                    ("onshape_document_id", "=", doc_id),
                ],
                limit=1,
            )
        )
        if not document:
            return
        try:
            with backend.work_on("onshape.backend") as work:
                adapter = work.component(usage="backend.adapter")
            doc_data = adapter.read_document(doc_id)
            vals = {}
            name = doc_data.get("name")
            if name and name != document.name:
                vals["name"] = name
            modified = doc_data.get("modifiedAt")
            if modified:
                try:
                    dt = datetime.fromisoformat(modified.replace("Z", "+00:00"))
                    vals["modified_at"] = dt.strftime("%Y-%m-%d %H:%M:%S")
                except (ValueError, TypeError):
                    _logger.debug("Could not parse modifiedAt %r", modified)
            if vals:
                document.write(vals)
                _logger.info("Document %s synced: %s", doc_id, vals)
        except Exception:
            _logger.exception("Failed to sync document %s", doc_id)
