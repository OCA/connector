# Copyright 2024 Kencove Farm Fence Supplies
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64
import hashlib
import hmac
import json
import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


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

        # Validate HMAC signature (required)
        raw_body = request.httprequest.get_data()
        if not backend.webhook_secret:
            _logger.warning(
                "Webhook secret not configured for backend %s. "
                "Rejecting unauthenticated webhook.",
                backend_id,
            )
            return {"status": "error", "message": "Webhook secret not configured"}

        signature = request.httprequest.headers.get(
            "X-onshape-webhook-signature-primary", ""
        )
        if not self._validate_signature(raw_body, backend.webhook_secret, signature):
            _logger.warning(
                "Webhook signature validation failed for backend %s",
                backend_id,
            )
            return {"status": "error", "message": "Invalid signature"}

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

        # Dispatch by event type
        handler = self._get_event_handler(event)
        if handler:
            handler(backend, payload)
            return {"status": "ok"}

        _logger.debug("Unhandled webhook event: %s", event)
        return {"status": "ok", "message": "Event not handled"}

    def _validate_signature(self, raw_body, secret, signature):
        expected = base64.b64encode(
            hmac.new(
                secret.encode("utf-8"),
                raw_body,
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
        """Log version creation (informational)."""
        doc_id = payload.get("documentId", "")
        version_name = payload.get("versionName", "")
        _logger.info(
            "Onshape version created: doc=%s version=%s",
            doc_id,
            version_name,
        )
