# Copyright 2024 Kencove Farm Fence Supplies
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


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
    team_id = fields.Char(string="Onshape Team / Company ID")
    webhook_secret = fields.Char(groups="base.group_system")
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

    def action_check_credentials(self):
        self.ensure_one()
        adapter = self._get_adapter()
        ok, message = adapter.check_credentials()
        if ok:
            self.write({"state": "checked"})
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Credentials Verified"),
                    "message": message,
                    "type": "success",
                    "sticky": False,
                },
            }
        raise UserError(_("Credential check failed: %s") % message)

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
