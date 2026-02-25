# Copyright 2024 Kencove Farm Fence Supplies
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class ProductProduct(models.Model):
    _inherit = "product.product"

    onshape_bind_ids = fields.One2many(
        "onshape.product.product",
        "odoo_id",
        string="Onshape Bindings",
    )
    onshape_linked = fields.Boolean(
        string="Linked to Onshape",
        compute="_compute_onshape_linked",
        store=True,
    )
    onshape_url = fields.Char(
        string="Onshape URL",
        compute="_compute_onshape_url",
    )

    @api.depends("onshape_bind_ids")
    def _compute_onshape_linked(self):
        for rec in self:
            rec.onshape_linked = bool(rec.onshape_bind_ids)

    @api.depends("onshape_bind_ids.onshape_url")
    def _compute_onshape_url(self):
        for rec in self:
            binding = rec.onshape_bind_ids[:1]
            rec.onshape_url = binding.onshape_url if binding else False
