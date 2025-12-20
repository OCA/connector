# Copyright 2025 Kencove
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html)

from datetime import timedelta

from odoo import api, fields, models


class AmazonCompetitivePrice(models.Model):
    """Store Amazon competitive pricing data for monitoring and repricing"""

    _name = "amazon.competitive.price"
    _description = "Amazon Competitive Price"
    _order = "fetch_date desc, id desc"

    product_binding_id = fields.Many2one(
        comodel_name="amazon.product.binding",
        string="Product Binding",
        required=True,
        ondelete="cascade",
        index=True,
    )
    product_id = fields.Many2one(
        comodel_name="product.product",
        string="Product",
        related="product_binding_id.odoo_id",
        store=True,
        index=True,
    )
    asin = fields.Char(
        string="ASIN",
        required=True,
        index=True,
        help="Amazon Standard Identification Number",
    )
    seller_sku = fields.Char(
        string="Seller SKU",
        related="product_binding_id.seller_sku",
        store=True,
    )
    marketplace_id = fields.Many2one(
        comodel_name="amazon.marketplace",
        string="Marketplace",
        required=True,
        ondelete="restrict",
    )
    backend_id = fields.Many2one(
        comodel_name="amazon.backend",
        string="Backend",
        related="product_binding_id.backend_id",
        store=True,
    )

    # Pricing data from Amazon API
    competitive_price_id = fields.Char(
        string="Competitive Price ID",
        help="Amazon's identifier for this competitive price point",
    )
    landed_price = fields.Monetary(
        help="Price including shipping (ListingPrice + Shipping)",
    )
    listing_price = fields.Monetary(
        help="Product price before shipping",
    )
    shipping_price = fields.Monetary(
        help="Shipping cost component",
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        string="Currency",
        required=True,
        default=lambda self: self.env.company.currency_id,
    )

    # Offer details
    condition = fields.Selection(
        selection=[
            ("New", "New"),
            ("Used", "Used"),
            ("Collectible", "Collectible"),
            ("Refurbished", "Refurbished"),
        ],
        default="New",
        required=True,
    )
    subcondition = fields.Char(
        help="More detailed condition (e.g., 'New', 'Like New', 'Very Good')",
    )
    offer_type = fields.Selection(
        selection=[
            ("BuyBox", "Buy Box"),
            ("Offer", "Competitive Offer"),
        ],
        help="Whether this is the Buy Box price or a competitive offer",
    )

    # Competitive landscape
    number_of_offers_new = fields.Integer(
        string="# New Offers",
        help="Total number of new condition offers",
    )
    number_of_offers_used = fields.Integer(
        string="# Used Offers",
        help="Total number of used condition offers",
    )

    # Buy Box indicators
    is_buy_box_winner = fields.Boolean(
        string="Buy Box Winner",
        help="True if this price represents the current Buy Box winner",
    )
    is_featured_merchant = fields.Boolean(
        string="Featured Merchant",
        help="True if seller is a Featured Merchant",
    )

    # Metadata
    fetch_date = fields.Datetime(
        required=True,
        default=fields.Datetime.now,
        index=True,
        help="When this pricing data was retrieved from Amazon",
    )
    active = fields.Boolean(
        default=True,
        help="Set to False for historical data",
    )

    # Calculated fields
    price_difference = fields.Monetary(
        string="Price vs. Our Price",
        compute="_compute_price_difference",
        store=True,
        help="Difference between competitive price and our current price",
    )
    our_current_price = fields.Monetary(
        compute="_compute_our_current_price",
        help="Our current selling price for this product",
    )

    _sql_constraints = [
        (
            "amazon_competitive_price_unique",
            "unique(product_binding_id, asin, competitive_price_id, fetch_date)",
            "This competitive price entry already exists.",
        ),
    ]

    @api.depends("listing_price", "product_binding_id.odoo_id.list_price")
    def _compute_price_difference(self):
        """Calculate difference between competitive price and our price"""
        for record in self:
            if record.listing_price and record.product_binding_id.odoo_id.list_price:
                record.price_difference = (
                    record.listing_price - record.product_binding_id.odoo_id.list_price
                )
            else:
                record.price_difference = 0.0

    @api.depends("product_binding_id.odoo_id.list_price")
    def _compute_our_current_price(self):
        """Get our current selling price"""
        for record in self:
            record.our_current_price = (
                record.product_binding_id.odoo_id.list_price or 0.0
            )

    def action_apply_to_pricelist(self):
        """Create/update pricelist item to match competitive price"""
        self.ensure_one()

        # Get or use shop pricelist
        shop = self.env["amazon.shop"].search(
            [
                ("backend_id", "=", self.backend_id.id),
                ("marketplace_id", "=", self.marketplace_id.id),
            ],
            limit=1,
        )

        if not shop or not shop.pricelist_id:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "No Pricelist",
                    "message": "No pricelist configured for this shop.",
                    "type": "warning",
                },
            }

        # Create or update pricelist item
        pricelist_item = self.env["product.pricelist.item"].search(
            [
                ("pricelist_id", "=", shop.pricelist_id.id),
                ("product_id", "=", self.product_id.id),
                ("compute_price", "=", "fixed"),
            ],
            limit=1,
        )

        vals = {
            "pricelist_id": shop.pricelist_id.id,
            "product_id": self.product_id.id,
            "fixed_price": self.listing_price,
            "compute_price": "fixed",
            "applied_on": "0_product_variant",
        }

        if pricelist_item:
            pricelist_item.write(vals)
        else:
            pricelist_item = self.env["product.pricelist.item"].create(vals)

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Price Updated",
                "message": (
                    f"Pricelist updated to {self.listing_price:.2f} "
                    f"{self.currency_id.name}"
                ),
                "type": "success",
            },
        }

    def action_view_product(self):
        """Open the related product form"""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "product.product",
            "res_id": self.product_id.id,
            "view_mode": "form",
            "target": "current",
        }

    @api.model
    def archive_old_prices(self, days=30):
        """Archive competitive prices older than specified days

        Args:
            days: Number of days to keep active (default 30)

        Returns:
            int: Number of records archived
        """
        cutoff_date = fields.Datetime.now() - timedelta(days=days)
        old_prices = self.search(
            [("fetch_date", "<", cutoff_date), ("active", "=", True)]
        )
        count = len(old_prices)
        old_prices.write({"active": False})
        return count
