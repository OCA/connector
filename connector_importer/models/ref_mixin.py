# -*- coding: utf-8 -*-
# Author: Simone Orsi
# Copyright 2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models, fields, api, tools

# TODO: not sure we need this to solve the source issue.


class ReferenceMixin(models.AbstractModel):
    """Mixin klass for generic model relationship."""

    _name = 'model.reference.mixin'

    ref_id = fields.Integer(
        "Ref. ID",
        required=True,
        ondelete="cascade",
    )
    ref_model = fields.Char(required=True)
    ref_item_id = fields.Reference(
        selection="_selection_ref_item_id",
        string="Referenced item",
        compute="_compute_ref_item_id",
        store=True,
    )

    @api.model
    @tools.ormcache("self")
    def _selection_ref_item_id(self):
        """Allow any model; after all, this field is readonly."""
        return [(r.model, r.name) for r in self._reference_models_search()]

    @api.multi
    @api.depends("ref_model", "ref_id")
    def _compute_ref_item_id(self):
        """Get a reference field based on the split model and id fields."""
        for item in self:
            if item.ref_model:
                item.ref_item_id = "{0.ref_model},{0.ref_id}".format(item)

    def _reference_models_search(self):
        return self.env["ir.model"].search([])
