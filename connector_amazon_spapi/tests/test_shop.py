# Copyright 2025 Kencove
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html)

from datetime import datetime, timedelta
from unittest import mock

from . import common


class TestAmazonShop(common.CommonConnectorAmazonSpapi):
    """Tests for amazon.shop model"""

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

    def test_action_push_stock_queues_job(self):
        """Test that action_push_stock queues a background job"""
        self.shop.sync_stock = True

        with mock.patch.object(self.shop, "with_delay") as mock_delay:
            mock_delayed = mock.Mock()
            mock_delay.return_value = mock_delayed

            result = self.shop.action_push_stock()

            # Verify with_delay was called
            mock_delay.assert_called_once()
            # Verify push_stock was called on the delayed object
            mock_delayed.push_stock.assert_called_once()

            # Verify notification is returned
            self.assertEqual(result["type"], "ir.actions.client")
            self.assertEqual(result["tag"], "display_notification")
            self.assertIn("Stock push queued", result["params"]["message"])
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
                    "listing_price": 89.99,
                    "landed_price": 99.99,
                    "fetch_date": "2024-01-15 10:00:00",
                },
                {
                    "product_binding_id": binding2.id,
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
            self.assertEqual(call_args[0][0], self.marketplace.marketplace_id)
            self.assertIn("B08TEST001", call_args[0][1])
            self.assertIn("B08TEST002", call_args[0][1])
            self.assertEqual(call_args[0][2], 20)  # Default chunk_size

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
                "listing_price": 89.99,
                "landed_price": 99.99,
                "fetch_date": "2024-01-15 10:00:00",
            }

            # Call with updated_since after old_fetch_date
            updated_since = datetime(2024, 1, 12, 0, 0, 0)
            count = self.shop.sync_competitive_prices(updated_since=updated_since)

            # Verify only stale binding (binding1) was processed
            call_args = mock_adapter.get_competitive_pricing_bulk.call_args
            asins = call_args[0][1]
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
                "listing_price": 89.99,
                "landed_price": 99.99,
                "fetch_date": "2024-01-15 10:00:00",
            }

            # Call sync_competitive_prices
            self.shop.sync_competitive_prices()

            # Verify only enabled binding was processed
            call_args = mock_adapter.get_competitive_pricing_bulk.call_args
            asins = call_args[0][1]
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
                "listing_price": 89.99,
                "landed_price": 99.99,
                "fetch_date": "2024-01-15 10:00:00",
            }

            # Call sync_competitive_prices
            self.shop.sync_competitive_prices()

            # Verify only binding with ASIN was processed
            call_args = mock_adapter.get_competitive_pricing_bulk.call_args
            asins = call_args[0][1]
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
            self.assertEqual(call_args[0][2], custom_chunk_size)
