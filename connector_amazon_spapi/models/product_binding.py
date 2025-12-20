from odoo import fields, models


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

    _sql_constraints = [
        (
            "amazon_product_unique",
            "unique(backend_id, seller_sku)",
            "A binding with this seller SKU already exists for the backend.",
        ),
    ]
