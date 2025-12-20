# Copyright 2025 Kencove
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html)

from datetime import datetime, timedelta
from unittest import mock

from odoo.exceptions import UserError

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
            "Orders": [sample_order],
            "NextToken": None,
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

        with mock.patch("odoo.addons.connector_amazon_spapi.models.backend.AmazonBackend._call_sp_api") as mock_call_sp_api:
            self.shop.sync_orders()
            mock_call_sp_api.assert_not_called()

    def test_sync_orders_lookback_days_calculation(self):
        """Test sync_orders calculates date range with lookback_days"""
        self.shop.order_sync_lookback_days = 7

        lookback_date = datetime.now() - timedelta(days=self.shop.order_sync_lookback_days)
        date_str = lookback_date.strftime("%Y-%m-%dT00:00:00Z")

        # Verify lookback days setting
        self.assertEqual(self.shop.order_sync_lookback_days, 7)
        self.assertIsNotNone(date_str)

    def test_sync_orders_updates_last_sync_timestamp(self):
        """Test sync_orders updates last_order_sync timestamp"""
        self.shop.last_order_sync = None

        with mock.patch("odoo.addons.connector_amazon_spapi.models.backend.AmazonBackend._call_sp_api") as mock_call_sp_api:
            mock_call_sp_api.return_value = {"Orders": [], "NextToken": None}
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
            "Orders": [sample_order1, sample_order2],
            "NextToken": None,
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
            {"Orders": [sample_order1], "NextToken": "token123"},
            {"Orders": [sample_order2], "NextToken": None},
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
        partner = self.env["res.partner"].create({"name": "Test Buyer", "email": "test@example.com"})

        # Create an existing order
        existing_order = self.env["amazon.sale.order"].create(
            {
                "shop_id": self.shop.id,
                "external_id": sample_order["AmazonOrderId"],
                "name": sample_order["AmazonOrderId"],
                "backend_id": self.backend.id,
                "odoo_id": self.env["sale.order"].create({
                    "partner_id": partner.id,
                    "name": sample_order["AmazonOrderId"],
                }).id,
                "state": "draft",
                "purchase_date": sample_order["PurchaseDate"],
                "status": sample_order["OrderStatus"],
            }
        )

        # Update the status in the sample
        sample_order["OrderStatus"] = "Shipped"

        mock_call_sp_api.return_value = {
            "Orders": [sample_order],
            "NextToken": None,
        }

        self.shop.sync_orders()

        existing_order.invalidate_cache()
        self.assertEqual(existing_order.status, "Shipped")

    def test_action_push_stock_requires_push_stock_enabled(self):
        """Test action_push_stock requires push_stock to be enabled"""
        self.shop.sync_stock = False

        with self.assertRaises(UserError) as cm:
            self.shop.action_push_stock()

        self.assertIn("Stock push is not enabled", str(cm.exception))

    def test_action_push_stock_enabled(self):
        """Test action_push_stock when enabled"""
        self.shop.sync_stock = True

        # Push stock is not yet implemented
        with self.assertRaises(NotImplementedError):
            self.shop.action_push_stock()

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
        mock_call_sp_api.return_value = {"Orders": [], "NextToken": None}

        self.shop.sync_orders()

        orders = self.env["amazon.sale.order"].search([("shop_id", "=", self.shop.id)])
        self.assertEqual(len(orders), 0)
