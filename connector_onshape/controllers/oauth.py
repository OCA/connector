# Copyright 2024 Kencove Farm Fence Supplies
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class OnshapeOAuthController(http.Controller):
    """Handle the OAuth2 authorization code callback from Onshape.

    Flow:
    1. User clicks "Authorize" on the Onshape backend form.
    2. Odoo redirects to https://oauth.onshape.com/oauth/authorize
    3. User approves on Onshape.
    4. Onshape redirects here with ?code=...
    5. We exchange the code for access + refresh tokens.

    Note: Onshape does not always return the ``state`` parameter in the
    callback, so we look up the pending backend by its stored CSRF token
    as a fallback.
    """

    def _resolve_backend(self, state):
        """Find the backend that initiated the OAuth flow.

        The ``state`` parameter is the plain CSRF token stored on the backend.
        If Onshape omits state, fall back to searching for a pending token.
        """
        Backend = request.env["onshape.backend"].sudo()

        if state:
            backend = Backend.search([("oauth2_csrf_token", "=", state)], limit=1)
            if backend:
                return backend, state

        # Onshape may omit state — find the backend with a pending CSRF token
        backend = Backend.search([("oauth2_csrf_token", "!=", False)], limit=1)
        if backend:
            return backend, backend.oauth2_csrf_token
        return None, None

    @http.route(
        "/connector_onshape/oauth/callback",
        type="http",
        auth="user",
        methods=["GET"],
        csrf=False,
    )
    def oauth_callback(self, **kwargs):
        error = kwargs.get("error")
        if error:
            error_desc = kwargs.get("error_description", error)
            _logger.error("OAuth2 error from Onshape: %s", error_desc)
            return request.redirect("/web")

        code = kwargs.get("code")
        if not code:
            _logger.error("OAuth2 callback missing code")
            return request.redirect("/web")

        state = kwargs.get("state")
        backend, csrf_token = self._resolve_backend(state)

        if not backend:
            _logger.error("OAuth2 callback: no pending backend found")
            return request.redirect("/web")

        # Verify CSRF token
        if not backend.oauth2_csrf_token or backend.oauth2_csrf_token != csrf_token:
            _logger.error("OAuth2 CSRF token mismatch for backend %s", backend.id)
            return request.redirect("/web")

        # Exchange code for token — include action so Odoo renders the menu
        action_id = request.env.ref(
            "connector_onshape.action_onshape_backend", raise_if_not_found=False
        )
        action_param = "&action=%d" % action_id.id if action_id else ""
        form_url = "/web#id=%d&model=onshape.backend&view_type=form%s" % (
            backend.id,
            action_param,
        )
        try:
            backend._oauth2_exchange_code(code)
            _logger.info("OAuth2 authorization successful for backend %s", backend.id)
        except Exception:
            _logger.exception("OAuth2 token exchange failed for backend %s", backend.id)
            # Clear the CSRF token so the user can retry
            backend.write({"oauth2_csrf_token": False})
            return request.redirect(form_url)

        # Redirect back to the backend form
        return request.redirect(form_url)
