from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    def _register_hook(self):
        """Ensure optional field used by connector views exists even without purchase.

        The upstream connector partner form references `supplier_invoice_count`, which
        normally comes from the purchase module. If purchase is not installed in this
        database, Odoo would fail view validation. We add a lightweight computed field
        at runtime when missing to keep the view loadable.
        """
        res = super()._register_hook()
        if "supplier_invoice_count" not in self._fields:
            field = fields.Integer(
                string="# Vendor Bills",
                compute="_compute_supplier_invoice_count_fallback",
            )
            self._add_field("supplier_invoice_count", field)
            field.setup(self)
        return res

    def _compute_supplier_invoice_count_fallback(self):
        for partner in self:
            partner.supplier_invoice_count = 0
