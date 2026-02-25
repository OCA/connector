# Copyright 2024 Kencove Farm Fence Supplies
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    onshape_document_count = fields.Integer(
        string="Onshape Documents",
        compute="_compute_onshape_document_count",
    )

    @api.depends(
        "product_variant_ids.onshape_bind_ids",
        "product_variant_ids.onshape_bind_ids.onshape_document_id",
    )
    def _compute_onshape_document_count(self):
        for rec in self:
            doc_ids = set()
            for variant in rec.product_variant_ids:
                for bind in variant.onshape_bind_ids:
                    if bind.onshape_document_id:
                        doc_ids.add(bind.onshape_document_id.id)
            rec.onshape_document_count = len(doc_ids)
