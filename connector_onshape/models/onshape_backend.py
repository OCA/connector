# Copyright 2024 Kencove Farm Fence Supplies
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import json
import logging
import secrets
from urllib.parse import quote, urlencode

import requests as req_lib

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

ONSHAPE_OAUTH_AUTHORIZE = "https://oauth.onshape.com/oauth/authorize"
ONSHAPE_OAUTH_TOKEN = "https://oauth.onshape.com/oauth/token"


class OnshapeBackend(models.Model):
    _name = "onshape.backend"
    _description = "Onshape Backend"
    _inherit = "connector.backend"

    name = fields.Char(required=True, default="Onshape")
    base_url = fields.Char(
        string="Base URL",
        required=True,
        default="https://cad.onshape.com",
    )
    auth_mode = fields.Selection(
        [("hmac", "HMAC (API Key)"), ("oauth2", "OAuth2 (App Store)")],
        string="Authentication Mode",
        required=True,
        default="hmac",
    )
    api_key = fields.Char(string="API Access Key", groups="base.group_system")
    api_secret = fields.Char(string="API Secret Key", groups="base.group_system")
    oauth2_client_id = fields.Char(
        string="OAuth2 Client ID", groups="base.group_system"
    )
    oauth2_client_secret = fields.Char(
        string="OAuth2 Client Secret", groups="base.group_system"
    )
    oauth2_token = fields.Text(string="OAuth2 Token (JSON)", groups="base.group_system")
    oauth2_csrf_token = fields.Char(groups="base.group_system")
    oauth2_authorized = fields.Boolean(
        compute="_compute_oauth2_authorized",
        string="OAuth2 Authorized",
    )
    oauth2_redirect_uri = fields.Char(
        compute="_compute_oauth2_redirect_uri",
        string="OAuth2 Redirect URI",
        help="Register this URL in your Onshape app's redirect URLs.",
    )
    onshape_company_id = fields.Char(
        string="Onshape Company ID",
        help="Enterprise/Professional plan company ID. "
        "Required for company-wide webhooks. "
        "Leave empty on Education/Student plans.",
    )
    webhook_secret = fields.Char(groups="base.group_system")
    webhook_url = fields.Char(
        compute="_compute_webhook_url",
        string="Webhook URL",
    )
    state = fields.Selection(
        [("draft", "Draft"), ("checked", "Checked"), ("active", "Active")],
        default="draft",
        required=True,
    )
    import_products_since = fields.Datetime()
    auto_create_products = fields.Boolean(
        string="Auto-create Products",
        help="Automatically create Odoo products for unmatched Onshape parts.",
    )
    default_product_category_id = fields.Many2one(
        "product.category",
        string="Default Product Category",
        help="Category assigned to auto-created products.",
    )
    document_ids = fields.One2many("onshape.document", "backend_id", string="Documents")
    document_count = fields.Integer(compute="_compute_document_count")
    product_binding_ids = fields.One2many(
        "onshape.product.product", "backend_id", string="Product Bindings"
    )
    product_binding_count = fields.Integer(compute="_compute_product_binding_count")
    bom_binding_ids = fields.One2many(
        "onshape.mrp.bom", "backend_id", string="BOM Bindings"
    )
    bom_binding_count = fields.Integer(compute="_compute_bom_binding_count")

    def _compute_oauth2_authorized(self):
        for rec in self:
            token_str = rec.oauth2_token or "{}"
            try:
                token_data = json.loads(token_str)
            except (ValueError, TypeError):
                token_data = {}
            rec.oauth2_authorized = bool(token_data.get("access_token"))

    def _compute_oauth2_redirect_uri(self):
        base_url = self.env["ir.config_parameter"].sudo().get_param("web.base.url")
        uri = "%s/connector_onshape/oauth/callback" % base_url
        for rec in self:
            rec.oauth2_redirect_uri = uri

    def _compute_webhook_url(self):
        base_url = self.env["ir.config_parameter"].sudo().get_param("web.base.url")
        for rec in self:
            if isinstance(rec.id, int):
                rec.webhook_url = "%s/connector_onshape/webhook/%d" % (
                    base_url,
                    rec.id,
                )
            else:
                rec.webhook_url = False

    @api.depends("document_ids")
    def _compute_document_count(self):
        for rec in self:
            rec.document_count = len(rec.document_ids)

    @api.depends("product_binding_ids")
    def _compute_product_binding_count(self):
        for rec in self:
            rec.product_binding_count = len(rec.product_binding_ids)

    @api.depends("bom_binding_ids")
    def _compute_bom_binding_count(self):
        for rec in self:
            rec.bom_binding_count = len(rec.bom_binding_ids)

    def _get_adapter(self):
        self.ensure_one()
        with self.work_on("onshape.backend") as work:
            return work.component(usage="backend.adapter")

    # --- OAuth2 flow ---

    def action_oauth2_authorize(self):
        """Redirect to Onshape OAuth2 authorization page."""
        self.ensure_one()
        if not self.oauth2_client_id:
            raise UserError(_("Please set the OAuth2 Client ID and Secret first."))
        csrf_token = secrets.token_urlsafe(32)
        self.write({"oauth2_csrf_token": csrf_token})
        # Onshape rejects JSON in the state parameter — use a plain opaque token.
        # The callback resolves the backend by matching oauth2_csrf_token.
        params = {
            "response_type": "code",
            "client_id": self.oauth2_client_id,
            "redirect_uri": self.oauth2_redirect_uri,
            "state": csrf_token,
        }
        auth_url = "%s?%s" % (
            ONSHAPE_OAUTH_AUTHORIZE,
            urlencode(params, quote_via=quote),
        )
        return {
            "type": "ir.actions.act_url",
            "url": auth_url,
            "target": "self",
        }

    def _oauth2_exchange_code(self, code):
        """Exchange authorization code for access + refresh tokens."""
        self.ensure_one()
        redirect_uri = self.oauth2_redirect_uri
        client_id = (self.oauth2_client_id or "").strip()
        client_secret = (self.oauth2_client_secret or "").strip()
        # Onshape requires credentials in the POST body (not Basic Auth).
        # Use a raw string body so the trailing '=' in client_id/secret
        # is sent literally (not URL-encoded as %3D).
        body = (
            "grant_type=authorization_code"
            "&code=%s"
            "&redirect_uri=%s"
            "&client_id=%s"
            "&client_secret=%s"
        ) % (
            code,
            quote(redirect_uri, safe=""),
            client_id,
            client_secret,
        )
        resp = req_lib.post(
            ONSHAPE_OAUTH_TOKEN,
            data=body,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=30,
        )
        if resp.status_code != 200:
            _logger.error(
                "OAuth2 token exchange failed for backend %s: %s",
                self.id,
                resp.text[:200],
            )
            resp.raise_for_status()
        token_data = resp.json()
        self.write(
            {
                "oauth2_token": json.dumps(token_data),
                "oauth2_csrf_token": False,
            }
        )
        _logger.info("OAuth2 token obtained for backend %s", self.id)

    def _oauth2_refresh_token(self):
        """Refresh an expired OAuth2 access token."""
        self.ensure_one()
        try:
            token_data = json.loads(self.oauth2_token or "{}")
        except (ValueError, TypeError):
            return {}
        refresh_token = token_data.get("refresh_token")
        if not refresh_token:
            _logger.error("No refresh token for backend %s — re-authorize.", self.id)
            return {}
        # Raw string body — Onshape may not decode %3D in client_id
        body = (
            "grant_type=refresh_token"
            "&refresh_token=%s"
            "&client_id=%s"
            "&client_secret=%s"
        ) % (
            refresh_token,
            (self.oauth2_client_id or "").strip(),
            (self.oauth2_client_secret or "").strip(),
        )
        resp = req_lib.post(
            ONSHAPE_OAUTH_TOKEN,
            data=body,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=30,
        )
        if resp.status_code != 200:
            _logger.error(
                "OAuth2 refresh failed for backend %s: %s",
                self.id,
                resp.text[:200],
            )
            return {}
        new_token_data = resp.json()
        self.write({"oauth2_token": json.dumps(new_token_data)})
        _logger.info("OAuth2 token refreshed for backend %s", self.id)
        return new_token_data

    # --- Credential check ---

    def action_check_credentials(self):
        self.ensure_one()
        if self.auth_mode == "oauth2":
            # Use sudo() to read the group-restricted oauth2_token field
            sudo_rec = self.sudo()
            token_str = sudo_rec.oauth2_token or ""
            csrf_pending = bool(sudo_rec.oauth2_csrf_token)
            try:
                token_data = json.loads(token_str) if token_str else {}
            except (ValueError, TypeError):
                token_data = {}
            if not token_data.get("access_token"):
                if csrf_pending:
                    raise UserError(
                        _(
                            "OAuth2 authorization is still pending. "
                            "Please complete the authorization in the Onshape "
                            "window that was opened, then try again."
                        )
                    )
                if token_str and not token_data.get("access_token"):
                    raise UserError(
                        _(
                            "OAuth2 token was saved but does not contain an "
                            "access_token. The token exchange may have failed. "
                            "Please click 'Authorize with Onshape' to retry. "
                            "Check the server logs for details."
                        )
                    )
                raise UserError(
                    _(
                        "No OAuth2 token found. Please click "
                        "'Authorize with Onshape' to start the "
                        "authorization flow, approve access on Onshape, "
                        "and wait to be redirected back."
                    )
                )
        adapter = self._get_adapter()
        ok, message = adapter.check_credentials()
        if not ok:
            raise UserError(_("Credential check failed: %s") % message)
        self.write({"state": "checked"})

    def action_activate(self):
        self.ensure_one()
        if self.state != "checked":
            raise UserError(_("Please check credentials first."))
        self.write({"state": "active"})

    def action_import_documents(self):
        self.ensure_one()
        self._check_active()
        with self.work_on("onshape.document") as work:
            importer = work.component(usage="batch.importer")
            importer.run(backend=self)

    def action_import_products(self):
        self.ensure_one()
        self._check_active()
        with self.work_on("onshape.product.product") as work:
            importer = work.component(usage="batch.importer")
            importer.run(backend=self)

    def action_import_products_for_document(self, document):
        """Import products for a single document (webhook-triggered)."""
        self.ensure_one()
        self._check_active()
        with self.work_on("onshape.product.product") as work:
            importer = work.component(usage="batch.importer")
            importer.run(backend=self, documents=document)

    def action_import_boms(self):
        self.ensure_one()
        self._check_active()
        with self.work_on("onshape.mrp.bom") as work:
            importer = work.component(usage="batch.importer")
            importer.run(backend=self)

    def action_export_part_numbers(self):
        self.ensure_one()
        self._check_active()
        bindings = self.product_binding_ids.filtered(lambda b: b.odoo_id.default_code)
        for binding in bindings:
            binding.with_delay().export_record()

    def action_generate_webhook_secret(self):
        """Generate a random webhook secret."""
        self.ensure_one()
        self.write({"webhook_secret": secrets.token_hex(32)})

    def _cleanup_webhooks(self):
        """Delete stale/duplicate webhooks for this backend's URL.

        Compares webhook IDs from Onshape against tracked IDs stored on
        documents.  Only deletes untracked (stale) webhooks; leaves
        tracked ones in place so we don't needlessly re-register.
        """
        adapter = self._get_adapter()
        base_url = self.env["ir.config_parameter"].sudo().get_param("web.base.url")
        webhook_url = "%s/connector_onshape/webhook/%d" % (base_url, self.id)
        result = adapter.list_webhooks()
        items = result.get("items", []) if isinstance(result, dict) else []

        # Collect tracked webhook IDs from documents
        tracked_ids = set(
            self.document_ids.filtered("onshape_webhook_id").mapped(
                "onshape_webhook_id"
            )
        )

        deleted = 0
        for hook in items:
            if hook.get("url") != webhook_url:
                continue
            hook_id = hook.get("id", "")
            if hook_id in tracked_ids:
                # This webhook is tracked by a document — keep it
                continue
            adapter.delete_webhook(hook_id)
            deleted += 1

        if deleted:
            _logger.info(
                "Cleaned up %d stale webhook(s) for backend %s",
                deleted,
                self.id,
            )
        return deleted

    def _register_document_webhook(self, document):
        """Register a webhook for a single document and store the ID.

        Returns True if successful, False otherwise.
        """
        self.ensure_one()
        base_url = self.env["ir.config_parameter"].sudo().get_param("web.base.url")
        webhook_url = "%s/connector_onshape/webhook/%d" % (base_url, self.id)
        adapter = self._get_adapter()
        try:
            result = adapter.register_webhook(
                webhook_url, document_id=document.onshape_document_id
            )
            webhook_id = result.get("id", "") if isinstance(result, dict) else ""
            if webhook_id:
                document.write({"onshape_webhook_id": webhook_id})
                _logger.info(
                    "Registered webhook %s for document %s (%s)",
                    webhook_id,
                    document.name,
                    document.onshape_document_id,
                )
                return True
            _logger.warning(
                "Webhook registration returned no ID for document %s",
                document.onshape_document_id,
            )
        except Exception:
            _logger.exception(
                "Failed to register webhook for document %s (%s)",
                document.name,
                document.onshape_document_id,
            )
        return False

    def action_register_webhook(self):
        self.ensure_one()
        self._check_active()
        base_url = self.env["ir.config_parameter"].sudo().get_param("web.base.url")
        webhook_url = "%s/connector_onshape/webhook/%d" % (base_url, self.id)

        if self.onshape_company_id:
            # Enterprise path: company-wide webhook, clean up + register
            self._cleanup_webhooks()
            adapter = self._get_adapter()
            adapter.register_webhook(webhook_url)
            message = _("Company-wide webhook registered.")
        else:
            # Per-document path: clean up untracked webhooks, then register
            # only for documents that don't already have a tracked webhook.
            documents = self.document_ids
            if not documents:
                return {
                    "type": "ir.actions.client",
                    "tag": "display_notification",
                    "params": {
                        "title": _("No Documents"),
                        "message": _(
                            "No documents imported yet. Please click "
                            "'Import Documents' first, then register webhooks."
                        ),
                        "type": "warning",
                        "sticky": False,
                    },
                }
            # Remove stale/duplicate webhooks (keeps tracked ones).
            deleted = self._cleanup_webhooks()
            # Only register for documents still missing a webhook.
            need_webhook = documents.filtered(lambda d: not d.onshape_webhook_id)
            if not need_webhook and not deleted:
                return {
                    "type": "ir.actions.client",
                    "tag": "display_notification",
                    "params": {
                        "title": _("Webhooks Up To Date"),
                        "message": _(
                            "All %d document(s) already have active " "webhooks."
                        )
                        % len(documents),
                        "type": "info",
                        "sticky": False,
                    },
                }
            registered = 0
            for doc in need_webhook:
                if self._register_document_webhook(doc):
                    registered += 1
            message = _(
                "Webhooks registered for %(registered)d document(s). "
                "%(deleted)d stale webhook(s) removed."
            ) % {"registered": registered, "deleted": deleted}

        _logger.info("Webhook registered for backend %s", self.id)
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Webhook Registered"),
                "message": message,
                "type": "success",
                "sticky": False,
            },
        }

    def _check_active(self):
        if self.state != "active":
            raise UserError(
                _("Backend must be active. Please check credentials and activate.")
            )

    def action_open_documents(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Onshape Documents"),
            "res_model": "onshape.document",
            "view_mode": "tree,form",
            "domain": [("backend_id", "=", self.id)],
            "context": {"default_backend_id": self.id},
        }

    def action_open_product_bindings(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Onshape Product Bindings"),
            "res_model": "onshape.product.product",
            "view_mode": "tree,form",
            "domain": [("backend_id", "=", self.id)],
            "context": {"default_backend_id": self.id},
        }

    def action_open_bom_bindings(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Onshape BOM Bindings"),
            "res_model": "onshape.mrp.bom",
            "view_mode": "tree,form",
            "domain": [("backend_id", "=", self.id)],
            "context": {"default_backend_id": self.id},
        }

    @api.model
    def cron_import_documents(self):
        backends = self.search([("state", "=", "active")])
        for backend in backends:
            backend.with_delay().action_import_documents()

    @api.model
    def cron_import_products(self):
        backends = self.search([("state", "=", "active")])
        for backend in backends:
            backend.with_delay().action_import_products()

    @api.model
    def cron_import_boms(self):
        backends = self.search([("state", "=", "active")])
        for backend in backends:
            backend.with_delay().action_import_boms()
