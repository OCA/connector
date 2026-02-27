# Copyright 2024 Kencove Farm Fence Supplies
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class OnshapeImportWizard(models.TransientModel):
    _name = "onshape.import.wizard"
    _description = "Onshape Import Wizard"

    backend_id = fields.Many2one(
        "onshape.backend",
        string="Backend",
        required=True,
        default=lambda self: self._default_backend_id(),
    )
    import_type = fields.Selection(
        [
            ("documents", "Documents Only"),
            ("products", "Documents + Products"),
            ("boms", "Documents + Products + BOMs"),
            ("full", "Full Sync (All)"),
        ],
        required=True,
        default="products",
    )
    auto_create_products = fields.Boolean(
        string="Auto-create Products",
        help="Create new Odoo products for unmatched Onshape parts.",
        default=lambda self: self._default_backend_id().auto_create_products,
    )

    @api.model
    def _default_backend_id(self):
        return self.env["onshape.backend"].search([("state", "=", "active")], limit=1)

    def action_import(self):
        self.ensure_one()
        backend = self.backend_id
        if backend.state != "active":
            raise UserError(_("Backend must be active. Check credentials first."))

        backend.write({"auto_create_products": self.auto_create_products})

        if self.import_type in ("documents", "products", "boms", "full"):
            backend.with_delay().action_import_documents()

        if self.import_type in ("products", "boms", "full"):
            backend.with_delay().action_import_products()

        if self.import_type in ("boms", "full"):
            backend.with_delay().action_import_boms()

        if self.import_type == "full":
            backend.with_delay().action_export_part_numbers()

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Import Started"),
                "message": _(
                    "Import jobs have been queued. " "Check the job queue for progress."
                ),
                "type": "success",
                "sticky": False,
                "next": {
                    "type": "ir.actions.act_window",
                    "res_model": "onshape.backend",
                    "res_id": backend.id,
                    "view_mode": "form",
                },
            },
        }
