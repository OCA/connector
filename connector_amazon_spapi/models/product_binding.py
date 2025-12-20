from odoo import _, fields, models
from odoo.exceptions import UserError


class AmazonProductBinding(models.Model):
    _name = "amazon.product.binding"
    _description = "Amazon Product Binding"
    _inherit = "external.binding"
    _inherits = {"product.product": "odoo_id"}

    odoo_id = fields.Many2one(
        comodel_name="product.product",
        string="Odoo Product",
        required=True,
        ondelete="cascade",
    )
    backend_id = fields.Many2one(
        comodel_name="amazon.backend",
        string="Backend",
        required=True,
        ondelete="restrict",
    )
    marketplace_id = fields.Many2one(
        comodel_name="amazon.marketplace", string="Marketplace", ondelete="restrict"
    )
    external_id = fields.Char(string="External ID")
    seller_sku = fields.Char(string="Seller SKU", required=True)
    asin = fields.Char(string="ASIN")
    fulfillment_channel = fields.Selection(
        selection=[("FBM", "Fulfilled by Merchant"), ("AFN", "Fulfilled by Amazon")],
        default="FBM",
    )
    lead_time_days = fields.Integer(string="Lead Time (days)", default=0)
    handling_time_days = fields.Integer(string="Handling Time (days)", default=0)
    stock_buffer = fields.Integer(
        string="Safety Stock Buffer",
        default=0,
        help="Units to hold back when syncing stock.",
    )
    sync_price = fields.Boolean(default=True)
    sync_stock = fields.Boolean(default=True)
    last_price_sync = fields.Datetime()
    last_stock_sync = fields.Datetime()

    competitive_price_ids = fields.One2many(
        comodel_name="amazon.competitive.price",
        inverse_name="product_binding_id",
        string="Competitive Prices",
    )
    competitive_price_count = fields.Integer(
        string="# Competitive Prices",
        compute="_compute_competitive_price_count",
    )

    _sql_constraints = [
        (
            "amazon_product_unique",
            "unique(backend_id, seller_sku)",
            "A binding with this seller SKU already exists for the backend.",
        ),
    ]

    def _compute_competitive_price_count(self):
        """Count active competitive prices for this binding"""
        for record in self:
            record.competitive_price_count = len(
                record.competitive_price_ids.filtered("active")
            )

    def action_fetch_competitive_prices(self):
        """Fetch competitive pricing from Amazon SP-API"""
        self.ensure_one()

        if not self.asin:
            raise UserError(_("This product has no ASIN assigned."))

        if not self.marketplace_id:
            raise UserError(_("No marketplace assigned to this product."))

        # Use pricing adapter to fetch competitive prices via work_on context
        with self.backend_id.work_on("amazon.product.binding") as work:
            adapter = work.component(usage="pricing.adapter")
            result = adapter.get_competitive_pricing(
                marketplace_id=self.marketplace_id.marketplace_id,
                asins=[self.asin],
            )

        if not result or not isinstance(result, list):
            raise UserError(_("No competitive pricing data returned from Amazon API."))

        # Use mapper to transform API response via work_on context
        with self.backend_id.work_on("amazon.product.binding") as work:
            mapper = work.component(
                usage="import.mapper", model_name="amazon.product.binding"
            )

        competitive_price_vals_list = []
        for pricing_data in result:
            vals = mapper.map_competitive_price(pricing_data, self)
            if vals:
                competitive_price_vals_list.append(vals)

        if not competitive_price_vals_list:
            raise UserError(
                _(
                    "No competitive pricing data found for ASIN %(asin)s "
                    "in marketplace %(marketplace)s"
                )
                % {
                    "asin": self.asin,
                    "marketplace": self.marketplace_id.name,
                }
            )

        # Create competitive price records
        self.env["amazon.competitive.price"].create(competitive_price_vals_list)

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Success"),
                "message": _("%d competitive price(s) fetched successfully")
                % len(competitive_price_vals_list),
                "type": "success",
            },
        }

    def action_view_competitive_prices(self):
        """Open competitive prices for this binding"""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Competitive Prices for %s") % self.display_name,
            "res_model": "amazon.competitive.price",
            "view_mode": "tree,form",
            "domain": [("product_binding_id", "=", self.id)],
            "context": {
                "default_product_binding_id": self.id,
                "default_asin": self.asin,
                "default_marketplace_id": self.marketplace_id.id,
            },
        }
