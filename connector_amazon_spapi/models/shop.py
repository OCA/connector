import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)


class AmazonShop(models.Model):
    _name = "amazon.shop"
    _description = "Amazon Shop"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char(required=True)
    backend_id = fields.Many2one(
        comodel_name="amazon.backend",
        required=True,
        ondelete="cascade",
    )
    marketplace_id = fields.Many2one(
        comodel_name="amazon.marketplace",
        required=True,
        ondelete="restrict",
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        required=True,
        default=lambda self: self.env.company,
    )
    warehouse_id = fields.Many2one(comodel_name="stock.warehouse")
    pricelist_id = fields.Many2one(
        comodel_name="product.pricelist",
        string="Amazon Pricelist",
        help="Pricelist to store pulled Amazon prices (e.g., KEN-A).",
    )
    payment_journal_id = fields.Many2one(
        comodel_name="account.journal",
        help="Optional journal to use when confirming imported orders.",
    )
    default_salesperson_id = fields.Many2one(
        comodel_name="res.users",
        help="Salesperson to assign on imported orders.",
    )
    default_sales_team_id = fields.Many2one(
        comodel_name="crm.team",
        help="Sales team to assign on imported orders.",
    )
    import_orders = fields.Boolean(default=True)
    sync_stock = fields.Boolean(string="Push Stock", default=True)
    sync_price = fields.Boolean(string="Push Prices", default=True)
    stock_sync_interval = fields.Selection(
        selection=[
            ("manual", "Manual Only"),
            ("hourly", "Every Hour"),
            ("daily", "Daily at Midnight"),
            ("realtime", "Real-time (on stock change)"),
        ],
        default="manual",
        string="Stock Sync Frequency",
        help="How often to push stock updates to Amazon.",
    )
    order_sync_interval = fields.Selection(
        selection=[
            ("manual", "Manual Only"),
            ("hourly", "Every Hour"),
            ("daily", "Daily at Midnight"),
        ],
        default="hourly",
        string="Order Sync Frequency",
        help="How often to import orders from Amazon.",
    )
    include_afn = fields.Boolean(
        string="Include AFN Orders",
        help="If enabled, also import Amazon-fulfilled orders.",
    )
    stock_policy = fields.Selection(
        selection=[("free", "Free Quantity"), ("forecast", "Forecast Quantity")],
        default="free",
        string="Stock Source",
    )
    last_order_sync = fields.Datetime()
    last_stock_sync = fields.Datetime()
    order_sync_lookback_days = fields.Integer(
        string="Order Lookback (days)",
        default=7,
        help="Used when no last sync is set.",
    )
    add_exp_line = fields.Boolean(
        string="Add Extra Routing Line",
        help="If enabled, add a configurable extra line to imported orders (e.g., /EXP-AMZ).",
        default=False,
    )
    exp_line_product_id = fields.Many2one(
        comodel_name="product.product",
        string="Extra Line Product",
        help="Product to use for the extra line. If not set, the extra line will be skipped.",
    )
    exp_line_name = fields.Char(
        string="Extra Line Description",
        default="/EXP-AMZ",
    )
    exp_line_qty = fields.Float(
        string="Extra Line Quantity",
        default=1.0,
    )
    exp_line_price = fields.Float(
        string="Extra Line Unit Price",
        default=0.0,
    )
    active = fields.Boolean(default=True)
    note = fields.Text(string="Notes")

    def action_sync_orders(self):
        """Trigger order sync in background"""
        for shop in self:
            shop.with_delay().sync_orders()

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Order Sync Queued",
                "message": f"Order synchronization job(s) queued for {len(self)} shop(s).",
                "type": "success",
                "sticky": False,
            },
        }

    def sync_orders(self):
        """Sync orders from Amazon SP-API"""
        self.ensure_one()
        from datetime import datetime, timedelta

        from odoo.exceptions import UserError

        if not self.import_orders:
            return

        # Calculate date range
        if self.last_order_sync:
            created_after = self.last_order_sync.isoformat()
        else:
            created_after = (
                datetime.now() - timedelta(days=self.order_sync_lookback_days)
            ).isoformat()

        # Call SP-API Orders endpoint
        params = {
            "MarketplaceIds": self.marketplace_id.marketplace_id,
            "CreatedAfter": created_after,
        }

        try:
            result = self.backend_id._call_sp_api(
                "GET",
                "/orders/v0/orders",
                params=params,
            )

            orders = result.get("payload", {}).get("Orders", [])

            # Process each order
            order_model = self.env["amazon.sale.order"]
            for amazon_order in orders:
                order_model._create_or_update_from_amazon(self, amazon_order)

            # Update last sync timestamp
            self.write({"last_order_sync": datetime.now()})

            return len(orders)
        except Exception as e:
            raise UserError(f"Failed to sync orders for {self.name}: {str(e)}") from e

    def action_sync_catalog(self):
        """Fetch Amazon listings and create/update product bindings"""
        for shop in self:
            shop.with_delay().sync_catalog()

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Catalog Sync Queued",
                "message": (
                    f"Catalog synchronization job(s) queued "
                    f"for {len(self)} shop(s)."
                ),
                "type": "success",
                "sticky": False,
            },
        }

    def sync_catalog(self):
        """Sync product listings from Amazon Catalog Items API

        Fetches active listings and creates amazon.product.binding records
        for products that exist on Amazon Seller Central.

        Ref: https://developer-docs.amazon.com/sp-api/docs/
        catalog-items-api-v2020-12-01-reference
        """
        self.ensure_one()
        from odoo.exceptions import UserError

        try:
            # Call Catalog Items API to get active listings
            # Note: This uses the ListingsItems endpoint for seller's active inventory
            params = {
                "MarketplaceIds": self.marketplace_id.marketplace_id,
                "IncludedData": "summaries",
            }

            result = self.backend_id._call_sp_api(
                "GET",
                "/listings/2021-08-01/items",
                params=params,
            )

            listings = result.get("listings", [])
            binding_model = self.env["amazon.product.binding"]
            created_count = 0
            updated_count = 0

            for listing in listings:
                sku = listing.get("sku")
                asin = listing.get("asin")

                if not sku:
                    continue

                # Check if binding already exists
                binding = binding_model.search(
                    [
                        ("backend_id", "=", self.backend_id.id),
                        ("seller_sku", "=", sku),
                    ],
                    limit=1,
                )

                if binding:
                    # Update existing binding
                    binding.write(
                        {
                            "asin": asin or binding.asin,
                            "marketplace_id": self.marketplace_id.id,
                        }
                    )
                    updated_count += 1
                else:
                    # Try to match by SKU in Odoo default_code
                    product = self.env["product.product"].search(
                        [("default_code", "=", sku)], limit=1
                    )

                    if not product:
                        # Log unmapped product - manual intervention needed
                        _logger.warning(
                            "Amazon listing found with SKU %s but no matching Odoo product. "
                            "Create product with default_code=%s or manually create binding.",
                            sku,
                            sku,
                        )
                        continue

                    # Create new binding
                    binding_model.create(
                        {
                            "backend_id": self.backend_id.id,
                            "marketplace_id": self.marketplace_id.id,
                            "odoo_id": product.id,
                            "seller_sku": sku,
                            "asin": asin,
                            "sync_stock": True,
                            "sync_price": True,
                        }
                    )
                    created_count += 1

            _logger.info(
                "Catalog sync for shop %s: %d created, %d updated",
                self.name,
                created_count,
                updated_count,
            )
            return {"created": created_count, "updated": updated_count}

        except Exception as e:
            raise UserError(f"Failed to sync catalog for {self.name}: {str(e)}") from e

    def action_push_stock(self):
        """Push inventory levels to Amazon"""
        for shop in self:
            shop.with_delay().push_stock()

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Stock Push Queued",
                "message": f"Stock update job(s) queued for {len(self)} shop(s).",
                "type": "success",
                "sticky": False,
            },
        }

    def cron_push_stock(self):
        """Cron job to push stock for all shops based on their sync interval."""
        # Hourly shops
        hourly_shops = self.search(
            [
                ("sync_stock", "=", True),
                ("stock_sync_interval", "=", "hourly"),
                ("active", "=", True),
            ]
        )
        if hourly_shops:
            hourly_shops.action_push_stock()

        # Daily shops (run at midnight)
        from datetime import datetime

        if datetime.now().hour == 0:
            daily_shops = self.search(
                [
                    ("sync_stock", "=", True),
                    ("stock_sync_interval", "=", "daily"),
                    ("active", "=", True),
                ]
            )
            if daily_shops:
                daily_shops.action_push_stock()

    def cron_sync_orders(self):
        """Cron job to import orders for shops based on their order sync interval."""
        from datetime import datetime

        # Hourly shops
        hourly_shops = self.search(
            [
                ("import_orders", "=", True),
                ("order_sync_interval", "=", "hourly"),
                ("active", "=", True),
            ]
        )
        if hourly_shops:
            hourly_shops.action_sync_orders()

        # Daily shops (run at midnight)
        if datetime.now().hour == 0:
            daily_shops = self.search(
                [
                    ("import_orders", "=", True),
                    ("order_sync_interval", "=", "daily"),
                    ("active", "=", True),
                ]
            )
            if daily_shops:
                daily_shops.action_sync_orders()

    def cron_push_shipments(self):
        """Cron job to push shipment tracking for shipped orders."""
        order_bindings = self.env["amazon.sale.order"].search(
            [
                ("backend_id", "=", self.backend_id.id),
                ("shipment_confirmed", "=", False),
            ]
        )

        for binding in order_bindings:
            picking = binding._get_last_done_picking()
            if not picking:
                continue
            # Only push if tracking is present
            if not (picking.carrier_id and picking.carrier_tracking_ref):
                continue
            try:
                binding.with_delay().push_shipment()
            except Exception:
                # let the job record the error; continue others
                continue

    def push_stock(self):
        """Push stock levels to Amazon via Feeds API"""
        self.ensure_one()
        if not self.sync_stock:
            return

        # Get all active product bindings for this shop
        bindings = self.env["amazon.product.binding"].search(
            [
                ("backend_id", "=", self.backend_id.id),
                ("sync_stock", "=", True),
            ]
        )

        if not bindings:
            return

        # Build inventory feed XML following Amazon's specification
        feed_xml = self._build_inventory_feed_xml(bindings)

        # Create feed record for tracking
        feed = self.env["amazon.feed"].create(
            {
                "backend_id": self.backend_id.id,
                "feed_type": "POST_INVENTORY_AVAILABILITY_DATA",
                "state": "draft",
                "payload_json": feed_xml,
            }
        )

        # Submit feed via SP-API asynchronously
        feed.with_delay().submit_feed()

        # Update last sync timestamp
        self.last_stock_sync = fields.Datetime.now()

    def _build_inventory_feed_xml(self, bindings):
        """Build XML feed for inventory updates per Amazon specification.

        Returns XML string following Amazon's Inventory Feed schema.
        Ref: https://sellercentral.amazon.com/gp/help/200386250
        """
        xml_lines = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<AmazonEnvelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"',
            '    xsi:noNamespaceSchemaLocation="amzn-envelope.xsd">',
            "  <Header>",
            "    <DocumentVersion>1.01</DocumentVersion>",
            f"    <MerchantIdentifier>{self.backend_id.lwa_client_id}</MerchantIdentifier>",
            "  </Header>",
            "  <MessageType>Inventory</MessageType>",
        ]

        for idx, binding in enumerate(bindings, start=1):
            # Calculate available quantity considering safety buffer
            available_qty = max(
                0, binding.product_id.qty_available - binding.safety_stock_buffer
            )

            xml_lines.extend(
                [
                    "  <Message>",
                    f"    <MessageID>{idx}</MessageID>",
                    "    <Inventory>",
                    f"      <SKU>{binding.seller_sku}</SKU>",
                    "      <Quantity>",
                    f"        <Available>{int(available_qty)}</Available>",
                    "      </Quantity>",
                    "    </Inventory>",
                    "  </Message>",
                ]
            )

        xml_lines.append("</AmazonEnvelope>")
        return "\n".join(xml_lines)
