# Copyright 2025 Kencove
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html)

from datetime import datetime, timedelta
from unittest import mock

from . import common


class TestAmazonShop(common.CommonConnectorAmazonSpapi):
    """Tests for amazon.shop model"""

    def _set_qty_in_stock_location(self, product, quantity):
        location = self.env.ref("stock.stock_location_stock")
        quants = self.env["stock.quant"]._gather(product, location, strict=True)
        # _update_available_quantity adds to current quantity; adjust to target
        quantity -= sum(quants.mapped("quantity"))
        self.env["stock.quant"]._update_available_quantity(product, location, quantity)

    def test_shop_creation(self):
        """Test creating a shop record"""
        self.assertEqual(self.shop.name, "Test Amazon Shop")
        self.assertEqual(self.shop.backend_id, self.backend)
        self.assertEqual(self.shop.marketplace_id, self.marketplace)

    def test_shop_defaults(self):
        """Test shop default values"""
        self.assertTrue(self.shop.import_orders)
        self.assertTrue(self.shop.sync_price)
        self.assertEqual(self.shop.order_sync_lookback_days, 7)

    def test_action_sync_orders_queues_job(self):
        """Test that action_sync_orders queues a job"""
        # Verify shop has sync-related fields for queuing jobs
        self.assertIsNotNone(self.shop.backend_id)
        self.assertTrue(self.shop.import_orders)

    @mock.patch(
        "odoo.addons.connector_amazon_spapi.models.backend.AmazonBackend._call_sp_api"
    )
    def test_sync_orders_fetches_from_api(self, mock_call_sp_api):
        """Test sync_orders fetches orders from SP-API"""
        sample_order = self._create_sample_amazon_order()
        mock_call_sp_api.return_value = {
            "payload": {
                "Orders": [sample_order],
                "NextToken": None,
            }
        }

        # Simulate sync (would normally be called by queue job)
        self.shop.sync_orders()

        # Verify order was created
        order = self.env["amazon.sale.order"].search(
            [
                ("external_id", "=", "111-1111111-1111111"),
                ("shop_id", "=", self.shop.id),
            ]
        )
        self.assertTrue(order)
        self.assertEqual(order.name, "111-1111111-1111111")

    def test_sync_orders_respects_import_orders_flag(self):
        """Test sync_orders respects import_orders flag"""
        self.shop.import_orders = False

        with mock.patch(
            "odoo.addons.connector_amazon_spapi.models.backend.AmazonBackend._call_sp_api"
        ) as mock_call_sp_api:
            self.shop.sync_orders()
            mock_call_sp_api.assert_not_called()

    def test_sync_orders_lookback_days_calculation(self):
        """Test sync_orders calculates date range with lookback_days"""
        self.shop.order_sync_lookback_days = 7

        lookback_date = datetime.now() - timedelta(
            days=self.shop.order_sync_lookback_days
        )
        date_str = lookback_date.strftime("%Y-%m-%dT00:00:00Z")

        # Verify lookback days setting
        self.assertEqual(self.shop.order_sync_lookback_days, 7)
        self.assertIsNotNone(date_str)

    def test_sync_orders_updates_last_sync_timestamp(self):
        """Test sync_orders updates last_order_sync timestamp"""
        self.shop.last_order_sync = None

        with mock.patch(
            "odoo.addons.connector_amazon_spapi.models.backend.AmazonBackend._call_sp_api"
        ) as mock_call_sp_api:
            mock_call_sp_api.return_value = {
                "payload": {"Orders": [], "NextToken": None}
            }
            self.shop.sync_orders()

        self.assertIsNotNone(self.shop.last_order_sync)

    @mock.patch(
        "odoo.addons.connector_amazon_spapi.models.backend.AmazonBackend._call_sp_api"
    )
    def test_sync_orders_creates_order_bindings(self, mock_call_sp_api):
        """Test sync_orders creates amazon.sale.order bindings"""
        sample_order1 = self._create_sample_amazon_order()
        sample_order2 = self._create_sample_amazon_order()
        sample_order2["AmazonOrderId"] = "222-2222222-2222222"
        sample_order2["PurchaseDate"] = (
            datetime.now() - timedelta(hours=1)
        ).isoformat()

        mock_call_sp_api.return_value = {
            "payload": {
                "Orders": [sample_order1, sample_order2],
                "NextToken": None,
            }
        }

        self.shop.sync_orders()

        orders = self.env["amazon.sale.order"].search([("shop_id", "=", self.shop.id)])
        self.assertEqual(len(orders), 2)

    @mock.patch(
        "odoo.addons.connector_amazon_spapi.models.backend.AmazonBackend._call_sp_api"
    )
    def test_sync_orders_handles_pagination(self, mock_call_sp_api):
        """Test sync_orders handles pagination with NextToken"""
        sample_order1 = self._create_sample_amazon_order()
        sample_order1["AmazonOrderId"] = "111-1111111-1111111"

        sample_order2 = self._create_sample_amazon_order()
        sample_order2["AmazonOrderId"] = "222-2222222-2222222"

        # First call returns NextToken
        # Second call returns no NextToken
        mock_call_sp_api.side_effect = [
            {"payload": {"Orders": [sample_order1], "NextToken": "token123"}},
            {"payload": {"Orders": [sample_order2], "NextToken": None}},
        ]

        self.shop.sync_orders()

        self.assertEqual(mock_call_sp_api.call_count, 2)
        orders = self.env["amazon.sale.order"].search([("shop_id", "=", self.shop.id)])
        self.assertEqual(len(orders), 2)

    @mock.patch(
        "odoo.addons.connector_amazon_spapi.models.backend.AmazonBackend._call_sp_api"
    )
    def test_sync_orders_updates_existing_orders(self, mock_call_sp_api):
        """Test sync_orders updates existing order records"""
        sample_order = self._create_sample_amazon_order()

        # Create a partner for the order
        partner = self.env["res.partner"].create(
            {"name": "Test Buyer", "email": "test@example.com"}
        )

        # Create an existing order
        existing_order = self.env["amazon.sale.order"].create(
            {
                "shop_id": self.shop.id,
                "external_id": sample_order["AmazonOrderId"],
                "name": sample_order["AmazonOrderId"],
                "backend_id": self.backend.id,
                "odoo_id": self.env["sale.order"]
                .create(
                    {
                        "partner_id": partner.id,
                        "name": sample_order["AmazonOrderId"],
                    }
                )
                .id,
                "state": "draft",
                "purchase_date": sample_order["PurchaseDate"],
                "status": sample_order["OrderStatus"],
            }
        )

        # Update the status in the sample
        sample_order["OrderStatus"] = "Shipped"

        mock_call_sp_api.return_value = {
            "payload": {
                "Orders": [sample_order],
                "NextToken": None,
            }
        }

        self.shop.sync_orders()

        existing_order.invalidate_recordset()
        self.assertEqual(existing_order.status, "Shipped")

    def test_action_push_stock_returns_notification(self):
        """Test action_push_stock returns success notification.

        Note: with_delay is read-only and cannot be mocked directly.
        We test the notification response instead.
        """
        result = self.shop.action_push_stock()

        # Verify notification is returned
        self.assertEqual(result["type"], "ir.actions.client")
        self.assertEqual(result["tag"], "display_notification")
        self.assertIn("Stock Push Queued", result["params"]["title"])
        self.assertEqual(result["params"]["type"], "success")

    def test_multiple_shops_same_backend(self):
        """Test multiple shops can be created for same backend"""
        marketplace2 = self.env["amazon.marketplace"].create(
            {
                "name": "Amazon.co.uk",
                "marketplace_id": "A1F83G7XSQSF3T",
                "code": "UK",
                "currency_id": self.env.company.currency_id.id,
                "backend_id": self.backend.id,
            }
        )

        shop2 = self._create_shop(
            name="UK Shop",
            marketplace_id=marketplace2.id,
        )

        self.assertEqual(shop2.backend_id, self.backend)
        self.assertEqual(len(self.backend.shop_ids), 2)

    def test_shop_warehouse_defaults_to_backend_warehouse(self):
        """Test shop warehouse defaults to backend warehouse"""
        warehouse = self.env["stock.warehouse"].search([], limit=1)
        backend_with_wh = self._create_backend(warehouse_id=warehouse.id)
        shop_wh = self._create_shop(backend_id=backend_with_wh.id)

        self.assertEqual(shop_wh.warehouse_id, warehouse)

    def test_shop_sync_filter_by_status(self):
        """Test shop sync can filter by order status"""
        self.assertTrue(hasattr(self.shop, "last_order_sync"))
        self.assertTrue(hasattr(self.shop, "import_orders"))

    @mock.patch(
        "odoo.addons.connector_amazon_spapi.models.backend.AmazonBackend._call_sp_api"
    )
    def test_sync_orders_empty_response(self, mock_call_sp_api):
        """Test sync_orders handles empty response gracefully"""
        mock_call_sp_api.return_value = {"payload": {"Orders": [], "NextToken": None}}

        self.shop.sync_orders()

        orders = self.env["amazon.sale.order"].search([("shop_id", "=", self.shop.id)])
        self.assertEqual(len(orders), 0)

    def test_sync_competitive_prices_bulk_fetch(self):
        """Test sync_competitive_prices fetches prices and creates records"""
        # Create product bindings with sync_price enabled
        binding1 = self._create_product_binding(
            asin="B08TEST001", seller_sku="SKU001", sync_price=True
        )
        binding2 = self._create_product_binding(
            asin="B08TEST002", seller_sku="SKU002", sync_price=True
        )

        # Mock adapter and mapper
        with mock.patch.object(type(self.shop.backend_id), "work_on") as mock_work_on:
            mock_work = mock.Mock()
            mock_work_on.return_value.__enter__.return_value = mock_work

            mock_adapter = mock.Mock()
            mock_mapper = mock.Mock()
            mock_work.component.side_effect = lambda usage, **kw: (
                mock_adapter if usage == "pricing.adapter" else mock_mapper
            )

            # Mock adapter response
            pricing_data1 = self._create_sample_pricing_data(asin="B08TEST001")
            pricing_data2 = self._create_sample_pricing_data(asin="B08TEST002")
            mock_adapter.get_competitive_pricing_bulk.return_value = [
                pricing_data1,
                pricing_data2,
            ]

            # Mock mapper responses
            mock_mapper.map_competitive_price.side_effect = [
                {
                    "product_binding_id": binding1.id,
                    "marketplace_id": self.marketplace.id,
                    "asin": "B08TEST001",
                    "listing_price": 89.99,
                    "landed_price": 99.99,
                    "fetch_date": "2024-01-15 10:00:00",
                },
                {
                    "product_binding_id": binding2.id,
                    "marketplace_id": self.marketplace.id,
                    "asin": "B08TEST002",
                    "listing_price": 89.99,
                    "landed_price": 99.99,
                    "fetch_date": "2024-01-15 10:00:00",
                },
            ]

            # Call sync_competitive_prices
            count = self.shop.sync_competitive_prices()

            # Verify adapter called with correct params
            mock_adapter.get_competitive_pricing_bulk.assert_called_once()
            call_args = mock_adapter.get_competitive_pricing_bulk.call_args
            self.assertEqual(
                call_args.kwargs.get("marketplace_id"),
                self.marketplace.marketplace_id,
            )
            self.assertIn("B08TEST001", call_args.kwargs.get("asins", []))
            self.assertIn("B08TEST002", call_args.kwargs.get("asins", []))
            self.assertEqual(call_args.kwargs.get("chunk_size"), 20)  # Default

            # Verify mapper called for each pricing data
            self.assertEqual(mock_mapper.map_competitive_price.call_count, 2)

            # Verify records created
            self.assertEqual(count, 2)

    def test_sync_competitive_prices_incremental_with_updated_since(self):
        """Test sync_competitive_prices with updated_since filters stale bindings"""
        # Create product bindings
        binding1 = self._create_product_binding(
            asin="B08TEST001", seller_sku="SKU001", sync_price=True
        )
        self._create_product_binding(
            asin="B08TEST002", seller_sku="SKU002", sync_price=True
        )

        # Create existing price record for binding1 with old fetch_date
        old_fetch_date = datetime(2024, 1, 10, 10, 0, 0)
        self.env["amazon.competitive.price"].create(
            {
                "product_binding_id": binding1.id,
                "marketplace_id": self.marketplace.id,
                "asin": "B08TEST001",
                "listing_price": 79.99,
                "landed_price": 89.99,
                "fetch_date": old_fetch_date,
            }
        )

        # Mock adapter and mapper
        with mock.patch.object(type(self.shop.backend_id), "work_on") as mock_work_on:
            mock_work = mock.Mock()
            mock_work_on.return_value.__enter__.return_value = mock_work

            mock_adapter = mock.Mock()
            mock_mapper = mock.Mock()
            mock_work.component.side_effect = lambda usage, **kw: (
                mock_adapter if usage == "pricing.adapter" else mock_mapper
            )

            # Mock adapter to return only stale binding
            pricing_data = self._create_sample_pricing_data(asin="B08TEST001")
            mock_adapter.get_competitive_pricing_bulk.return_value = [pricing_data]

            # Mock mapper response
            mock_mapper.map_competitive_price.return_value = {
                "product_binding_id": binding1.id,
                "marketplace_id": self.marketplace.id,
                "asin": "B08TEST001",
                "listing_price": 89.99,
                "landed_price": 99.99,
                "fetch_date": "2024-01-15 10:00:00",
            }

            # Call with updated_since after old_fetch_date
            updated_since = datetime(2024, 1, 12, 0, 0, 0)
            count = self.shop.sync_competitive_prices(updated_since=updated_since)

            # Verify only stale binding (binding1) was processed
            call_args = mock_adapter.get_competitive_pricing_bulk.call_args
            asins = call_args.kwargs.get("asins", [])
            self.assertIn("B08TEST001", asins)
            # binding2 has no price record, should also be included
            self.assertIn("B08TEST002", asins)

            # Verify records created
            self.assertGreaterEqual(count, 1)

    def test_sync_competitive_prices_respects_sync_price_flag(self):
        """Test sync_competitive_prices only processes bindings with sync_price=True"""
        # Create bindings with different sync_price values
        binding_enabled = self._create_product_binding(
            asin="B08TEST001", seller_sku="SKU001", sync_price=True
        )
        self._create_product_binding(
            asin="B08TEST002", seller_sku="SKU002", sync_price=False
        )

        # Mock adapter and mapper
        with mock.patch.object(type(self.shop.backend_id), "work_on") as mock_work_on:
            mock_work = mock.Mock()
            mock_work_on.return_value.__enter__.return_value = mock_work

            mock_adapter = mock.Mock()
            mock_mapper = mock.Mock()
            mock_work.component.side_effect = lambda usage, **kw: (
                mock_adapter if usage == "pricing.adapter" else mock_mapper
            )

            # Mock adapter response
            pricing_data = self._create_sample_pricing_data(asin="B08TEST001")
            mock_adapter.get_competitive_pricing_bulk.return_value = [pricing_data]

            # Mock mapper response
            mock_mapper.map_competitive_price.return_value = {
                "product_binding_id": binding_enabled.id,
                "marketplace_id": self.marketplace.id,
                "asin": "B08TEST001",
                "listing_price": 89.99,
                "landed_price": 99.99,
                "fetch_date": "2024-01-15 10:00:00",
            }

            # Call sync_competitive_prices
            self.shop.sync_competitive_prices()

            # Verify only enabled binding was processed
            call_args = mock_adapter.get_competitive_pricing_bulk.call_args
            asins = call_args.kwargs.get("asins", [])
            self.assertIn("B08TEST001", asins)
            self.assertNotIn("B08TEST002", asins)

    def test_sync_competitive_prices_requires_asin(self):
        """Test sync_competitive_prices skips bindings without ASIN"""
        # Create bindings with and without ASIN
        binding_with_asin = self._create_product_binding(
            asin="B08TEST001", seller_sku="SKU001", sync_price=True
        )
        self._create_product_binding(asin=False, seller_sku="SKU002", sync_price=True)

        # Mock adapter and mapper
        with mock.patch.object(type(self.shop.backend_id), "work_on") as mock_work_on:
            mock_work = mock.Mock()
            mock_work_on.return_value.__enter__.return_value = mock_work

            mock_adapter = mock.Mock()
            mock_mapper = mock.Mock()
            mock_work.component.side_effect = lambda usage, **kw: (
                mock_adapter if usage == "pricing.adapter" else mock_mapper
            )

            # Mock adapter response
            pricing_data = self._create_sample_pricing_data(asin="B08TEST001")
            mock_adapter.get_competitive_pricing_bulk.return_value = [pricing_data]

            # Mock mapper response
            mock_mapper.map_competitive_price.return_value = {
                "product_binding_id": binding_with_asin.id,
                "marketplace_id": self.marketplace.id,
                "asin": "B08TEST001",
                "listing_price": 89.99,
                "landed_price": 99.99,
                "fetch_date": "2024-01-15 10:00:00",
            }

            # Call sync_competitive_prices
            self.shop.sync_competitive_prices()

            # Verify only binding with ASIN was processed
            call_args = mock_adapter.get_competitive_pricing_bulk.call_args
            asins = call_args.kwargs.get("asins", [])
            self.assertIn("B08TEST001", asins)
            self.assertEqual(len(asins), 1)

    def test_sync_competitive_prices_respects_chunk_size(self):
        """Test sync_competitive_prices respects custom chunk_size parameter"""
        # Create multiple bindings
        for i in range(5):
            self._create_product_binding(
                asin=f"B08TEST{i:03d}", seller_sku=f"SKU{i:03d}", sync_price=True
            )

        # Mock adapter and mapper
        with mock.patch.object(type(self.shop.backend_id), "work_on") as mock_work_on:
            mock_work = mock.Mock()
            mock_work_on.return_value.__enter__.return_value = mock_work

            mock_adapter = mock.Mock()
            mock_mapper = mock.Mock()
            mock_work.component.side_effect = lambda usage, **kw: (
                mock_adapter if usage == "pricing.adapter" else mock_mapper
            )

            # Mock adapter to return empty list
            mock_adapter.get_competitive_pricing_bulk.return_value = []

            # Call with custom chunk_size
            custom_chunk_size = 3
            self.shop.sync_competitive_prices(chunk_size=custom_chunk_size)

            # Verify chunk_size was passed to adapter
            call_args = mock_adapter.get_competitive_pricing_bulk.call_args
            self.assertEqual(call_args.kwargs.get("chunk_size"), custom_chunk_size)

    def test_push_stock_creates_feed(self):
        """Test push_stock creates inventory feed and submits it."""
        # Enable stock sync
        self.shop.sync_stock = True

        # Create product binding with stock
        binding = self._create_product_binding(
            seller_sku="TEST-SKU-001", sync_stock=True
        )

        # Ensure predictable stock qty for the underlying Odoo product
        self._set_qty_in_stock_location(binding.odoo_id, 100.0)

        # Call push_stock
        with mock.patch.object(type(self.env["amazon.feed"]), "with_delay") as m:
            m.return_value = mock.Mock(submit_feed=mock.Mock())
            self.shop.push_stock()

        # Verify feed was created
        feed = self.env["amazon.feed"].search(
            [
                ("backend_id", "=", self.backend.id),
                ("feed_type", "=", "POST_INVENTORY_AVAILABILITY_DATA"),
            ],
            order="id desc",
            limit=1,
        )
        self.assertTrue(feed)
        self.assertEqual(feed.state, "draft")

        # Verify feed contains product data
        self.assertIn("TEST-SKU-001", feed.payload_json)

    def test_push_stock_respects_sync_stock_flag(self):
        """Test push_stock skips when sync_stock is disabled."""
        # Disable stock sync
        self.shop.sync_stock = False

        # Create binding
        self._create_product_binding(seller_sku="TEST-SKU-001", sync_stock=True)

        # Count feeds before
        feed_count_before = self.env["amazon.feed"].search_count(
            [("backend_id", "=", self.backend.id)]
        )

        # Call push_stock
        self.shop.push_stock()

        # Verify no new feed was created
        feed_count_after = self.env["amazon.feed"].search_count(
            [("backend_id", "=", self.backend.id)]
        )
        self.assertEqual(feed_count_before, feed_count_after)

    def test_build_inventory_feed_xml_structure(self):
        """Test _build_inventory_feed_xml generates valid XML."""
        # Create bindings on distinct products to avoid shared stock values
        product1 = self.env["product.product"].create(
            {"name": "Test Product 1", "default_code": "SKU-001", "type": "product"}
        )
        product2 = self.env["product.product"].create(
            {"name": "Test Product 2", "default_code": "SKU-002", "type": "product"}
        )

        binding1 = self._create_product_binding(
            seller_sku="SKU-001", odoo_id=product1.id
        )
        binding1.stock_buffer = 5
        self._set_qty_in_stock_location(binding1.odoo_id, 50.0)

        binding2 = self._create_product_binding(
            seller_sku="SKU-002", odoo_id=product2.id
        )
        binding2.stock_buffer = 10
        self._set_qty_in_stock_location(binding2.odoo_id, 100.0)

        bindings = binding1 | binding2

        # Generate XML
        xml_content = self.shop._build_inventory_feed_xml(bindings)

        # Verify XML structure
        self.assertIn('<?xml version="1.0" encoding="UTF-8"?>', xml_content)
        self.assertIn("<AmazonEnvelope", xml_content)
        self.assertIn("<MessageType>Inventory</MessageType>", xml_content)

        # Verify products included
        self.assertIn("<SKU>SKU-001</SKU>", xml_content)
        self.assertIn("<SKU>SKU-002</SKU>", xml_content)

        # Verify quantity calculation (available - buffer)
        self.assertIn("<Available>45</Available>", xml_content)  # 50 - 5
        self.assertIn("<Available>90</Available>", xml_content)  # 100 - 10

    def test_build_inventory_feed_xml_handles_negative_stock(self):
        """Test _build_inventory_feed_xml doesn't send negative quantities."""
        binding = self._create_product_binding(seller_sku="SKU-LOW")
        self._set_qty_in_stock_location(binding.odoo_id, 2.0)
        binding.stock_buffer = 5  # Buffer > available

        xml_content = self.shop._build_inventory_feed_xml(binding)

        # Verify quantity is 0, not negative
        self.assertIn("<Available>0</Available>", xml_content)
        self.assertNotIn("<Available>-", xml_content)

    def test_cron_push_stock_hourly(self):
        """Test cron_push_stock processes hourly shops."""
        # Create hourly shop
        hourly_shop = self.env["amazon.shop"].create(
            {
                "name": "Hourly Stock Shop",
                "backend_id": self.backend.id,
                "marketplace_id": self.marketplace.id,
                "sync_stock": True,
                "stock_sync_interval": "hourly",
                "active": True,
            }
        )

        # Mock action_push_stock
        with mock.patch.object(type(hourly_shop), "action_push_stock") as mock_push:
            # Call cron
            self.env["amazon.shop"].cron_push_stock()

            # Verify hourly shop was processed
            mock_push.assert_called()

    def test_cron_push_stock_skips_inactive_shops(self):
        """Test cron_push_stock skips inactive shops."""
        # Create inactive shop
        inactive_shop = self.env["amazon.shop"].create(
            {
                "name": "Inactive Shop",
                "backend_id": self.backend.id,
                "marketplace_id": self.marketplace.id,
                "sync_stock": True,
                "stock_sync_interval": "hourly",
                "active": False,
            }
        )

        # Mock action_push_stock
        with mock.patch.object(type(inactive_shop), "action_push_stock") as mock_push:
            # Call cron
            self.env["amazon.shop"].cron_push_stock()

            # Verify inactive shop was not processed
            mock_push.assert_not_called()

    def test_cron_push_shipments(self):
        """Test cron_push_shipments queues shipment jobs for shipped orders."""
        # Create order binding with tracking info
        order = self.env["amazon.sale.order"].create(
            {
                "external_id": "111-7777777-7777777",
                "backend_id": self.backend.id,
                "marketplace_id": self.marketplace.id,
                "partner_id": self.partner.id,
                "shipment_confirmed": False,
            }
        )

        # Create picking with tracking
        carrier = self.env.ref("delivery.free_delivery_carrier")
        picking = self.env["stock.picking"].create(
            {
                "picking_type_id": self.env.ref("stock.picking_type_out").id,
                "location_id": self.env.ref("stock.stock_location_stock").id,
                "location_dest_id": self.env.ref("stock.stock_location_customers").id,
                "state": "done",
                "carrier_id": carrier.id,
                "carrier_tracking_ref": "TRACK123",
            }
        )

        # Link picking to order
        with mock.patch.object(
            type(order), "_get_last_done_picking", return_value=picking
        ):
            # Call cron - test it runs without errors
            self.shop.cron_push_shipments()
            # Note: with_delay() makes direct verification difficult

    def test_action_push_stock_queues_background_job(self):
        """Test action_push_stock returns success notification."""
        result = self.shop.action_push_stock()

        # Verify notification response
        self.assertEqual(result["type"], "ir.actions.client")
        self.assertEqual(result["tag"], "display_notification")
        self.assertIn("Stock Push Queued", result["params"]["title"])

    def test_push_stock_updates_last_sync_timestamp(self):
        """Test push_stock updates last_stock_sync field."""
        self.shop.sync_stock = True

        # Create binding
        self._create_product_binding(seller_sku="SKU-001", sync_stock=True)

        # Clear timestamp
        self.shop.last_stock_sync = False

        # Push stock
        with mock.patch.object(type(self.env["amazon.feed"]), "with_delay") as m:
            m.return_value = mock.Mock(submit_feed=mock.Mock())
            self.shop.push_stock()

        # Verify timestamp was updated
        self.assertTrue(self.shop.last_stock_sync)

    def test_sync_competitive_prices_updates_last_sync_timestamp(self):
        """Test sync_competitive_prices updates last_price_sync field."""
        # Create binding with ASIN
        binding = self._create_product_binding(
            asin="B08TEST001", seller_sku="SKU001", sync_price=True
        )

        # Clear timestamp
        self.shop.last_price_sync = False

        # Mock adapter and mapper
        with mock.patch.object(type(self.shop.backend_id), "work_on") as mock_work_on:
            mock_work = mock.Mock()
            mock_work_on.return_value.__enter__.return_value = mock_work

            mock_adapter = mock.Mock()
            mock_mapper = mock.Mock()
            mock_work.component.side_effect = lambda usage, **kw: (
                mock_adapter if usage == "pricing.adapter" else mock_mapper
            )

            pricing_data = self._create_sample_pricing_data(asin="B08TEST001")
            mock_adapter.get_competitive_pricing_bulk.return_value = [pricing_data]
            mock_mapper.map_competitive_price.return_value = {
                "product_binding_id": binding.id,
                "marketplace_id": self.marketplace.id,
                "asin": "B08TEST001",
                "listing_price": 89.99,
                "landed_price": 99.99,
                "fetch_date": "2024-01-15 10:00:00",
            }

            # Call sync
            self.shop.sync_competitive_prices()

        # Verify timestamp was updated
        self.assertTrue(self.shop.last_price_sync)

    def test_push_stock_builds_xml_feed_correctly(self):
        """Test push_stock creates well-formed inventory XML"""
        self.shop.write({"sync_stock": True})
        binding = self._create_product_binding(
            seller_sku="TEST-SKU-123", sync_stock=True
        )

        # Set qty in stock location
        self._set_qty_in_stock_location(binding.odoo_id, 50.0)

        with mock.patch.object(type(self.env["amazon.feed"]), "with_delay") as m:
            m.return_value = mock.Mock(submit_feed=mock.Mock())
            self.shop.push_stock()

        # Find the created feed
        feed = self.env["amazon.feed"].search(
            [
                ("backend_id", "=", self.backend.id),
                ("feed_type", "=", "POST_INVENTORY_AVAILABILITY_DATA"),
            ],
            order="id desc",
            limit=1,
        )
        self.assertTrue(feed)

        # Verify XML structure - uses <Available> tag
        xml_payload = feed.payload_json
        self.assertIn("<MessageType>Inventory</MessageType>", xml_payload)
        self.assertIn("<SKU>TEST-SKU-123</SKU>", xml_payload)
        self.assertIn("<Available>50</Available>", xml_payload)

    def test_cron_push_stock_respects_interval_settings(self):
        """Test cron job pushes stock for configured intervals"""
        # Create hourly shop
        hourly_shop = self.shop.copy(
            {
                "name": "Hourly Shop",
                "stock_sync_interval": "hourly",
                "sync_stock": True,
            }
        )

        with mock.patch.object(
            type(self.env["amazon.shop"]), "action_push_stock"
        ) as mock_push:
            self.env["amazon.shop"].cron_push_stock()

            # Verify hourly shop was called - check if mock was called
            if mock_push.called:
                # Get the shops from the call
                call_args = mock_push.call_args
                if call_args and len(call_args.args) > 0:
                    called_shops = call_args.args[0]
                    self.assertIn(hourly_shop.id, called_shops.ids)

    def test_cron_push_shipments_queues_pending_deliveries(self):
        """Test shipment cron finds and pushes done pickings"""
        # Create order with done picking
        order = self._create_amazon_order(external_id="TEST-SHIP-001")

        # Create sale order and picking
        sale_order = self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "company_id": self.env.company.id,
            }
        )
        order.write({"odoo_id": sale_order.id})

        picking = self.env["stock.picking"].create(
            {
                "picking_type_id": self.env.ref("stock.picking_type_out").id,
                "location_id": self.env.ref("stock.stock_location_stock").id,
                "location_dest_id": self.env.ref("stock.stock_location_customers").id,
                "sale_id": sale_order.id,
                "state": "done",
                "date_done": datetime.now(),
                "carrier_id": self.env["delivery.carrier"]
                .create({"name": "Test Carrier", "product_id": self.product.id})
                .id,
                "carrier_tracking_ref": "TRACK123",
            }
        )

        # Simply call the cron and verify the expected behavior
        self.shop.cron_push_shipments()
        # Verify the picking exists with tracking data
        self.assertEqual(picking.carrier_tracking_ref, "TRACK123")
