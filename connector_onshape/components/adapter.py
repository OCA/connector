# Copyright 2024 Kencove Farm Fence Supplies
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64
import hashlib
import hmac
import json
import logging
import secrets
import string
import threading
import time
from datetime import datetime
from urllib.parse import urlencode

import requests

from odoo.addons.component.core import Component

_logger = logging.getLogger(__name__)

MAX_RETRIES = 3
RETRY_BACKOFF = 5

# Per-backend lock for OAuth2 token refresh.  Prevents concurrent threads
# from refreshing at the same time (second refresh invalidates the first).
_OAUTH2_REFRESH_LOCKS = {}
_OAUTH2_LOCKS_LOCK = threading.Lock()


class OnshapeAdapter(Component):
    """API adapter for Onshape REST API.

    Supports HMAC authentication (ported from onshape_utils.py)
    and OAuth2 bearer tokens.

    Handles rate limiting (429), quota exhaustion (402), and retries.
    """

    _name = "onshape.adapter"
    _inherit = "onshape.base"
    _usage = "backend.adapter"

    # --- Authentication ---

    def _get_backend(self):
        return self.collection

    def _canonical_query(self, params):
        if not params:
            return ""
        return urlencode(sorted(params.items()), doseq=True)

    def _hmac_headers(self, method, path, query_params=None, content_type=""):
        """Generate HMAC auth headers.

        Ported from onshape_utils.py lines 52-94.
        Signing string: method, nonce, date, content_type, path, query
        All lowercased, HMAC-SHA256 signed, Base64 encoded.
        """
        backend = self._get_backend()
        method = method.upper()
        date = datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S GMT")
        alphabet = string.ascii_letters + string.digits
        nonce = "".join(secrets.choice(alphabet) for _ in range(25))
        canonical_query = self._canonical_query(query_params)

        string_to_sign = (
            method
            + "\n"
            + nonce
            + "\n"
            + date
            + "\n"
            + content_type
            + "\n"
            + path
            + "\n"
            + canonical_query
            + "\n"
        ).lower()

        sig_bytes = hmac.new(
            backend.api_secret.encode("utf-8"),
            string_to_sign.encode("utf-8"),
            digestmod=hashlib.sha256,
        ).digest()
        signature = base64.b64encode(sig_bytes).decode("utf-8")

        headers = {
            "Date": date,
            "Authorization": "On %s:HmacSHA256:%s" % (backend.api_key, signature),
            "On-Nonce": nonce,
            "Accept": "application/json",
        }
        if content_type:
            headers["Content-Type"] = content_type
        return headers

    def _oauth2_headers(self, content_type=""):
        backend = self._get_backend()
        try:
            token_data = json.loads(backend.oauth2_token or "{}")
        except (ValueError, TypeError):
            _logger.error("oauth2_token for backend %s is not valid JSON", backend.id)
            token_data = {}
        access_token = token_data.get("access_token", "")
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        }
        if content_type:
            headers["Content-Type"] = content_type
        return headers

    def _get_auth_headers(self, method, path, query_params=None, content_type=""):
        backend = self._get_backend()
        if backend.auth_mode == "oauth2":
            return self._oauth2_headers(content_type=content_type)
        return self._hmac_headers(
            method,
            path,
            query_params=query_params,
            content_type=content_type,
        )

    # --- HTTP request with retry ---

    def _log_rate_limit(self, resp):
        """Warn when Onshape rate-limit headroom is low."""
        remaining = resp.headers.get("X-Rate-Limit-Remaining")
        if remaining is None:
            return
        try:
            remaining_int = int(remaining)
            if remaining_int < 10:
                _logger.warning("Onshape rate limit low: %s remaining", remaining_int)
        except ValueError:
            _logger.debug("Non-integer rate limit header: %s", remaining)

    def _try_refresh_oauth2(self, resp, attempt):
        """Refresh OAuth2 token on 401 (first attempt only).

        Uses a per-backend lock so that when multiple threads hit 401
        simultaneously, only one performs the refresh and the others
        reuse the new token.
        """
        backend = self._get_backend()
        if resp.status_code != 401 or backend.auth_mode != "oauth2" or attempt != 0:
            return False

        # Get or create a lock for this backend
        backend_id = backend.id
        with _OAUTH2_LOCKS_LOCK:
            if backend_id not in _OAUTH2_REFRESH_LOCKS:
                _OAUTH2_REFRESH_LOCKS[backend_id] = threading.Lock()
            lock = _OAUTH2_REFRESH_LOCKS[backend_id]

        # Read the token that produced the 401 so we can detect if
        # another thread already refreshed while we waited for the lock.
        stale_token = (backend.oauth2_token or "")[:50]

        with lock:
            # Re-read from DB — another thread may have refreshed already
            backend.invalidate_recordset(["oauth2_token"])
            current_token = (backend.oauth2_token or "")[:50]
            if current_token != stale_token and current_token:
                _logger.info(
                    "OAuth2 token already refreshed by another thread, reusing"
                )
                return True

            new_token = backend._oauth2_refresh_token()
            if new_token.get("access_token"):
                _logger.info("OAuth2 token refreshed, retrying request")
                return True
        return False

    def _check_retryable(self, resp, attempt):
        """Return wait seconds if request should be retried, else None."""
        if resp.status_code == 402:
            backend = self._get_backend()
            if backend.auth_mode == "oauth2":
                _logger.error(
                    "Onshape API quota exhausted (402) with OAuth2. "
                    "Publish the app on the Onshape App Store to bypass "
                    "quota, or contact api-support@onshape.com."
                )
                raise OnshapeQuotaError(
                    "Onshape API quota exhausted. Your OAuth2 app must be "
                    "publicly published on the Onshape App Store to bypass "
                    "the annual limit. Contact api-support@onshape.com or "
                    "onshape-developer-relations@ptc.com."
                )
            _logger.error(
                "Onshape API quota exhausted (402). " "Consider switching to OAuth2."
            )
            raise OnshapeQuotaError(
                "Onshape API quota exhausted. "
                "Switch to OAuth2 App Store authentication."
            )
        if resp.status_code == 429:
            wait = RETRY_BACKOFF * (attempt + 1)
            retry_after = resp.headers.get("Retry-After")
            if retry_after:
                try:
                    wait = int(retry_after)
                except (TypeError, ValueError):
                    _logger.debug(
                        "Unexpected Retry-After header %r; using backoff %ss",
                        retry_after,
                        wait,
                    )
            _logger.warning("Onshape rate limited (429), waiting %ss", wait)
            return wait
        if resp.status_code >= 500:
            wait = RETRY_BACKOFF * (attempt + 1)
            _logger.warning(
                "Onshape server error %s, retry in %ss",
                resp.status_code,
                wait,
            )
            return wait
        return None

    def _request(self, method, path, query_params=None, json_body=None, raw=False):
        """Make an authenticated API request with retry and rate-limit handling.

        Ported from enrich_onshape_metadata.py lines 147-176.
        """
        backend = self._get_backend()
        content_type = "application/json" if json_body else ""
        url = f"{backend.base_url}{path}"
        last_resp = None

        for attempt in range(MAX_RETRIES):
            headers = self._get_auth_headers(
                method,
                path,
                query_params=query_params,
                content_type=content_type,
            )
            try:
                resp = requests.request(
                    method,
                    url,
                    headers=headers,
                    params=query_params,
                    json=json_body,
                    timeout=30,
                )
                last_resp = resp
                self._log_rate_limit(resp)

                # Refresh OAuth2 token on 401 and retry
                if self._try_refresh_oauth2(resp, attempt):
                    continue

                wait = self._check_retryable(resp, attempt)
                if wait is not None:
                    time.sleep(wait)
                    continue

                if raw:
                    return resp
                if resp.status_code >= 400:
                    _logger.error(
                        "Onshape API %s %s → %s: %s",
                        method,
                        path,
                        resp.status_code,
                        resp.text[:500],
                    )
                resp.raise_for_status()
                if resp.status_code == 204:
                    return {}
                return resp.json()

            except requests.exceptions.HTTPError:
                # Client/server HTTP errors — don't retry, let caller handle
                raise
            except requests.exceptions.RequestException:
                # Connection errors, timeouts — retry with backoff
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_BACKOFF)
                    continue
                raise

        if raw:
            return last_resp
        if last_resp is not None:
            last_resp.raise_for_status()
        return {}

    # --- Credential check ---

    def check_credentials(self):
        try:
            resp = self._request(
                "GET",
                "/api/v6/documents",
                query_params={"limit": 1},
                raw=True,
            )
            if resp.status_code == 200:
                return True, "Credentials verified (documents endpoint OK)."
            if resp.status_code == 401:
                return False, "Unauthorized (401). Check API key/secret."
            return (
                False,
                f"Unexpected status {resp.status_code}: " f"{resp.text[:200]}",
            )
        except OnshapeQuotaError as e:
            return False, str(e)
        except Exception as e:
            return False, f"Connection error: {e}"

    # --- Document endpoints ---

    def search_documents(self, owner_id=None, offset=0, limit=20):
        params = {"offset": offset, "limit": limit, "sortColumn": "name"}
        if owner_id:
            params["owner"] = owner_id
            params["ownerType"] = 1  # company
        return self._request("GET", "/api/v6/documents", query_params=params)

    def read_document(self, document_id):
        return self._request("GET", f"/api/v6/documents/{document_id}")

    def read_document_elements(self, document_id, workspace_id):
        return self._request(
            "GET",
            f"/api/v6/documents/d/{document_id}/w/{workspace_id}/elements",
        )

    # --- Part / Metadata endpoints ---

    def read_parts(self, document_id, workspace_id, element_id):
        return self._request(
            "GET",
            f"/api/v6/parts/d/{document_id}/w/{workspace_id}" f"/e/{element_id}",
        )

    def read_mass_properties(self, document_id, workspace_id, element_id, part_id=None):
        """Get computed mass properties (mass, volume, surface area).

        Returns dict with 'bodies' key containing per-body mass data.
        Each body has 'mass' (kg), 'volume' (m³), 'periphery' (m²).
        """
        params = {}
        if part_id:
            params["partId"] = part_id
        return self._request(
            "GET",
            f"/api/v6/parts/d/{document_id}/w/{workspace_id}"
            f"/e/{element_id}/massproperties",
            query_params=params if params else None,
        )

    def read_part_metadata(self, document_id, workspace_id, element_id):
        return self._request(
            "GET",
            f"/api/v6/metadata/d/{document_id}/w/{workspace_id}" f"/e/{element_id}",
        )

    def write_part_metadata(self, document_id, workspace_id, element_id, items):
        """Write metadata to parts.

        Ported from enrich_onshape_metadata.py lines 201-246.
        ``items`` is a list of dicts with 'href' and 'properties' keys.
        """
        return self._request(
            "POST",
            f"/api/v6/metadata/d/{document_id}/w/{workspace_id}" f"/e/{element_id}",
            json_body={"items": items},
        )

    # --- Assembly BOM endpoint ---

    def read_assembly_bom(self, document_id, workspace_id, element_id):
        return self._request(
            "GET",
            f"/api/v6/assemblies/d/{document_id}/w/{workspace_id}"
            f"/e/{element_id}/bom",
        )

    # --- Thumbnail ---

    def read_thumbnail(self, document_id, size="300x300"):
        resp = self._request(
            "GET",
            f"/api/v6/thumbnails/d/{document_id}/s/{size}",
            raw=True,
        )
        if resp.status_code == 200:
            return base64.b64encode(resp.content).decode("utf-8")
        return None

    # --- Webhooks ---

    # Events that can be registered per-document (no company required)
    DOCUMENT_EVENTS = [
        "onshape.model.lifecycle.metadata",
        "onshape.model.lifecycle.createversion",
    ]
    # Events that require a companyId (Enterprise/Professional plans only)
    COMPANY_EVENTS = [
        "onshape.workflow.transition",
        "onshape.revision.created",
    ]

    def register_webhook(self, url, events=None, document_id=None):
        backend = self._get_backend()
        if events is None:
            if backend.onshape_company_id:
                events = self.DOCUMENT_EVENTS + self.COMPANY_EVENTS
            else:
                events = self.DOCUMENT_EVENTS
        body = {
            "url": url,
            "events": events,
            "options": {"collapseEvents": True},
        }
        if backend.onshape_company_id:
            body["companyId"] = backend.onshape_company_id
        elif document_id:
            body["documentId"] = document_id
        return self._request("POST", "/api/v6/webhooks", json_body=body)

    def list_webhooks(self):
        return self._request("GET", "/api/v6/webhooks")

    def delete_webhook(self, webhook_id):
        try:
            return self._request("DELETE", f"/api/v6/webhooks/{webhook_id}")
        except requests.exceptions.HTTPError as e:
            if e.response is not None and e.response.status_code == 404:
                return {}  # Already deleted / expired
            raise


class OnshapeQuotaError(Exception):
    """Raised when Onshape returns 402 (quota exhausted)."""
