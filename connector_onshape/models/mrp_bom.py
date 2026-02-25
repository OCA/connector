# Copyright 2024 Kencove Farm Fence Supplies
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class MrpBom(models.Model):
    _inherit = "mrp.bom"

    onshape_bind_ids = fields.One2many(
        "onshape.mrp.bom",
        "odoo_id",
        string="Onshape Bindings",
    )
    onshape_linked = fields.Boolean(
        string="Linked to Onshape",
        compute="_compute_onshape_linked",
        store=True,
    )

    @api.depends("onshape_bind_ids")
    def _compute_onshape_linked(self):
        for rec in self:
            rec.onshape_linked = bool(rec.onshape_bind_ids)
