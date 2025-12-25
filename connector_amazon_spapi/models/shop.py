import logging
from datetime import datetime, timedelta

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools import config

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
    last_price_sync = fields.Datetime(
        string="Last Competitive Pricing Sync",
        readonly=True,
        help="Timestamp of last competitive pricing fetch.",
    )
    order_sync_lookback_days = fields.Integer(
        string="Order Lookback (days)",
        default=7,
        help="Used when no last sync is set.",
    )
    add_exp_line = fields.Boolean(
        string="Add Extra Routing Line",
        help=(
            "If enabled, add a configurable extra line to imported orders "
            "(e.g., /EXP-AMZ)."
        ),
        default=False,
    )
    exp_line_product_id = fields.Many2one(
        comodel_name="product.product",
        string="Extra Line Product",
        help=(
            "Product to use for the extra line. "
            "If not set, the extra line will be skipped."
        ),
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

    @api.model_create_multi
    def create(self, vals_list):
        # Handle batch creation - process each value dict
        for vals in vals_list:
            backend = None
            if vals.get("backend_id"):
                backend = self.env["amazon.backend"].browse(vals["backend_id"])
            if not vals.get("warehouse_id") and backend and backend.warehouse_id:
                vals["warehouse_id"] = backend.warehouse_id.id
        return super().create(vals_list)

    def action_sync_orders(self):
        """Trigger order sync in background"""
        for shop in self:
            shop.with_delay().sync_orders()

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Order Sync Queued",
                "message": (f"Order sync queued for {len(self)} shop(s)."),
                "type": "success",
                "sticky": False,
            },
        }

    def sync_orders(self):
        """Sync orders from Amazon SP-API"""
        self.ensure_one()
        if not self.import_orders:
            return

        # Calculate date range
        if self.last_order_sync:
            created_after = self.last_order_sync.isoformat()
        else:
            created_after = (
                datetime.now() - timedelta(days=self.order_sync_lookback_days)
            ).isoformat()

        # Call SP-API Orders endpoint with pagination support
        ids_list = [self.marketplace_id.marketplace_id] if self.marketplace_id else []
        params = {
            "MarketplaceIds": ",".join(ids_list),
            "CreatedAfter": created_after,
        }

        try:
            total_orders = 0
            next_token = None

            while True:
                if next_token:
                    params["NextToken"] = next_token

                # Use adapter for API calls via work_on context
                with self.backend_id.work_on("amazon.sale.order") as work:
                    adapter = work.component(usage="orders.adapter")
                    result = adapter.list_orders(
                        marketplace_id=self.marketplace_id.marketplace_id,
                        created_after=created_after if not next_token else None,
                        next_token=next_token,
                    )

                payload = result.get("payload", {})
                orders = payload.get("Orders", [])
                next_token = payload.get("NextToken")

                # Process each order
                order_model = self.env["amazon.sale.order"].with_context(
                    # Avoid consuming order-item API side effects during tests
                    amazon_skip_line_sync=config["test_enable"]
                    and not self.env.context.get("amazon_force_line_sync")
                )
                for amazon_order in orders:
                    order_model._create_or_update_from_amazon(self, amazon_order)

                total_orders += len(orders)

                # Break if no more pages
                if not next_token:
                    break

            # Update last sync timestamp
            self.write({"last_order_sync": datetime.now()})

            return total_orders
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
        try:
            # Call Catalog Items API to get active listings
            # Note: This uses the ListingsItems endpoint for seller's active inventory

            # Use adapter for API calls via work_on context
            with self.backend_id.work_on("amazon.product.binding") as work:
                adapter = work.component(usage="listings.adapter")
                # Fetch all listings for the seller and marketplace
                result = adapter.get_listings_item(
                    marketplace_ids=[self.marketplace_id.marketplace_id],
                )

            if isinstance(result, dict):
                listings = [result]
            elif isinstance(result, list):
                listings = result
            else:
                listings = []

            binding_model = self.env["amazon.product.binding"]
            created_count = 0
            updated_count = 0
            for listing in listings:
                sku = listing.get("sku", None)
                asin = None
                if (
                    listing.get("summaries")
                    and listing.get("summaries")[0]
                    and listing.get("summaries")[0].get("asin")
                ):
                    asin = listing["summaries"][0]["asin"]

                if not sku or not asin:
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
                            (
                                "Amazon listing SKU %s missing in Odoo. "
                                "Create product (default_code=%s) or create binding."
                            ),
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
        """Trigger stock push in background"""
        for shop in self:
            shop.with_delay().push_stock()

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Stock Push Queued",
                "message": (f"Stock push queued for {len(self)} shop(s)."),
                "type": "success",
                "sticky": False,
            },
        }

    def action_sync_competitive_prices(self):
        """Trigger competitive pricing sync in background"""
        for shop in self:
            shop.with_delay().sync_competitive_prices(
                updated_since=shop.last_price_sync
            )

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Competitive Pricing Sync Queued",
                "message": (f"Pricing sync queued for {len(self)} shop(s)."),
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

    @api.model
    def cron_sync_competitive_prices(self):
        """Cron job to sync competitive pricing for active shops with price sync enabled."""
        shops = self.search(
            [
                ("active", "=", True),
                ("sync_price", "=", True),
            ]
        )
        for shop in shops:
            try:
                shop.with_delay().sync_competitive_prices(
                    updated_since=shop.last_price_sync
                )
            except Exception:
                # Let job queue record errors; continue to next shop
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

        # Check if in read-only mode
        if self.backend_id.read_only_mode:
            _logger.info(
                "[READ-ONLY MODE] Would push stock for %d products to Amazon. "
                "Feed XML preview:\n%s",
                len(bindings),
                feed_xml[:1000] + ("..." if len(feed_xml) > 1000 else ""),
            )
            # Update last sync timestamp even in read-only mode
            self.last_stock_sync = fields.Datetime.now()
            return

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
        merchant_id = self.backend_id.lwa_client_id
        xml_lines = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<AmazonEnvelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"',
            '    xsi:noNamespaceSchemaLocation="amzn-envelope.xsd">',
            "  <Header>",
            "    <DocumentVersion>1.01</DocumentVersion>",
            "    <MerchantIdentifier>" + merchant_id + "</MerchantIdentifier>",
            "  </Header>",
            "  <MessageType>Inventory</MessageType>",
        ]

        for idx, binding in enumerate(bindings, start=1):
            # Calculate available quantity considering safety buffer
            available_qty = max(0, binding.odoo_id.qty_available - binding.stock_buffer)

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

    def sync_competitive_prices(self, updated_since=None, chunk_size=None):
        """Fetch competitive pricing for all price-synced bindings in this shop.

        If ``updated_since`` is provided, only bindings whose latest
        local competitive price ``fetch_date`` is older than that
        timestamp (or missing) will be refreshed. Otherwise, all
        eligible bindings are fetched.

        Results are fetched in chunks using the pricing adapter's bulk
        helper to respect API per-request limits.

        Args:
            updated_since (datetime|str): Optional threshold to limit refresh.
            chunk_size (int): Optional chunk size cap per request (<=20).

        Returns:
            int: Number of competitive price records created.
        """
        self.ensure_one()

        # Collect eligible product bindings (must have ASIN and price sync enabled)
        binding_domain = [
            ("backend_id", "=", self.backend_id.id),
            ("marketplace_id", "=", self.marketplace_id.id),
            ("sync_price", "=", True),
            ("asin", "!=", False),
        ]
        bindings = self.env["amazon.product.binding"].search(binding_domain)
        if not bindings:
            return 0

        # If incremental, determine which bindings are stale relative to updated_since
        if updated_since:
            groups = (
                self.env["amazon.competitive.price"].read_group(
                    domain=[("product_binding_id", "in", bindings.ids)],
                    fields=["product_binding_id", "fetch_date:max"],
                    groupby=["product_binding_id"],
                )
                or []
            )
            latest_map = {
                g["product_binding_id"][0]: g.get("fetch_date_max") for g in groups
            }

            def is_stale(b):
                last = latest_map.get(b.id)
                return (not last) or (last < updated_since)

            bindings = bindings.filtered(is_stale)

        if not bindings:
            return 0

        # Map ASIN -> binding for fast lookup when mapping results
        asin_to_binding = {b.asin: b for b in bindings}
        asins = list(asin_to_binding.keys())

        created_vals = []

        # Use adapter and mapper via work_on context
        with self.backend_id.work_on("amazon.product.binding") as work:
            adapter = work.component(usage="pricing.adapter")
            mapper = work.component(
                usage="import.mapper", model_name="amazon.product.binding"
            )

            results = adapter.get_competitive_pricing_bulk(
                marketplace_id=self.marketplace_id.marketplace_id,
                asins=asins,
                chunk_size=chunk_size or 20,
            )

            for pricing_data in results:
                asin = pricing_data.get("ASIN")
                binding = asin_to_binding.get(asin)
                if not binding:
                    continue
                vals = mapper.map_competitive_price(pricing_data, binding)
                if vals:
                    created_vals.append(vals)

        if not created_vals:
            return 0

        self.env["amazon.competitive.price"].create(created_vals)

        # Update last sync timestamp
        self.write({"last_price_sync": fields.Datetime.now()})

        return len(created_vals)
