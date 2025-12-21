# Copyright 2025 Kencove
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html)

from unittest import mock

from odoo.tests import tagged

from . import common


@tagged("post_install", "-at_install")
class TestAmazonAdapters(common.CommonConnectorAmazonSpapi):
    """Tests for Amazon SP-API adapters"""

    def test_orders_adapter_list_orders(self):
        """Test OrdersAdapter.list_orders calls backend correctly"""
        with self.backend.work_on("amazon.sale.order") as work:
            adapter = work.component(usage="orders.adapter")

            with mock.patch(
                "odoo.addons.connector_amazon_spapi.models.backend.AmazonBackend._call_sp_api",
                return_value={"Orders": []},
            ) as mock_call:
                adapter.list_orders(
                    marketplace_id="ATVPDKIKX0DER", created_after="2025-12-01T00:00:00Z"
                )

                mock_call.assert_called_once()
                call_args = mock_call.call_args
                self.assertEqual(call_args[0][0], "GET")
                self.assertEqual(call_args[0][1], "/orders/v0/orders")
                self.assertIn("MarketplaceIds", call_args[1]["params"])

    def test_orders_adapter_get_order(self):
        """Test OrdersAdapter.get_order calls backend correctly"""
        with self.backend.work_on("amazon.sale.order") as work:
            adapter = work.component(usage="orders.adapter")

            with mock.patch(
                "odoo.addons.connector_amazon_spapi.models.backend.AmazonBackend._call_sp_api",
                return_value={"Order": {}},
            ) as mock_call:
                adapter.get_order("111-1111111-1111111")

                mock_call.assert_called_once()
                call_args = mock_call.call_args
                self.assertEqual(call_args[0][0], "GET")
                self.assertIn("111-1111111-1111111", call_args[0][1])

    def test_orders_adapter_get_order_items(self):
        """Test OrdersAdapter.get_order_items calls backend correctly"""
        with self.backend.work_on("amazon.sale.order") as work:
            adapter = work.component(usage="orders.adapter")

            with mock.patch(
                "odoo.addons.connector_amazon_spapi.models.backend.AmazonBackend._call_sp_api",
                return_value={"OrderItems": []},
            ) as mock_call:
                adapter.get_order_items("111-1111111-1111111")

                mock_call.assert_called_once()
                call_args = mock_call.call_args
                self.assertEqual(call_args[0][0], "GET")
                self.assertIn("111-1111111-1111111", call_args[0][1])
                self.assertIn("orderitems", call_args[0][1].lower())

    def test_pricing_adapter_get_competitive_pricing(self):
        """Test PricingAdapter.get_competitive_pricing calls backend correctly"""
        with self.backend.work_on("amazon.product.binding") as work:
            adapter = work.component(usage="pricing.adapter")

            with mock.patch(
                "odoo.addons.connector_amazon_spapi.models.backend.AmazonBackend._call_sp_api",
                return_value={"Items": []},
            ) as mock_call:
                adapter.get_competitive_pricing(
                    marketplace_id="ATVPDKIKX0DER", asins=["B01ABCDEFG", "B02XYZABC"]
                )

                mock_call.assert_called_once()
                call_args = mock_call.call_args
                self.assertEqual(call_args[0][0], "GET")
                self.assertIn("competitivePrice", call_args[0][1])
                self.assertIn("Asins", call_args[1]["params"])

    def test_pricing_adapter_get_competitive_pricing_with_skus(self):
        """Test PricingAdapter.get_competitive_pricing with SKUs"""
        with self.backend.work_on("amazon.product.binding") as work:
            adapter = work.component(usage="pricing.adapter")

            with mock.patch(
                "odoo.addons.connector_amazon_spapi.models.backend.AmazonBackend._call_sp_api",
                return_value={"Items": []},
            ) as mock_call:
                adapter.get_competitive_pricing(
                    marketplace_id="ATVPDKIKX0DER", skus=["TEST-SKU-001"]
                )

                mock_call.assert_called_once()
                call_args = mock_call.call_args
                self.assertIn("Skus", call_args[1]["params"])

    def test_pricing_adapter_enforces_max_items(self):
        """Test PricingAdapter enforces max 20 ASINs/SKUs"""
        with self.backend.work_on("amazon.product.binding") as work:
            adapter = work.component(usage="pricing.adapter")

            # Create 25 ASINs (exceeds limit)
            too_many_asins = [f"B{str(i).zfill(9)}" for i in range(25)]

            # Mock the API call to prevent 401 error
            with mock.patch(
                "odoo.addons.connector_amazon_spapi.models.backend.AmazonBackend._call_sp_api"
            ):
                with self.assertRaises(ValueError) as context:
                    adapter.get_competitive_pricing(
                        marketplace_id="ATVPDKIKX0DER", asins=too_many_asins
                    )

                self.assertIn("maximum of 20", str(context.exception))

    def test_inventory_adapter_create_inventory_feed(self):
        """Test InventoryAdapter.create_inventory_feed calls backend correctly"""
        with self.backend.work_on("amazon.product.binding") as work:
            adapter = work.component(usage="inventory.adapter")

            feed_content = """<?xml version="1.0" encoding="UTF-8"?>
                <AmazonEnvelope><MessageType>Inventory</MessageType></AmazonEnvelope>"""

            with mock.patch(
                "odoo.addons.connector_amazon_spapi.models.backend.AmazonBackend._call_sp_api",
                side_effect=[
                    {"feedDocumentId": "doc-123"},  # create_feed_document response
                    {"feedId": "123"},  # create_feed response
                ],
            ) as mock_call:
                result = adapter.create_inventory_feed(
                    feed_content=feed_content,
                    marketplace_ids=[self.marketplace.marketplace_id],
                )

                # Should call _call_sp_api twice (create_feed_document, then create_feed)
                self.assertEqual(mock_call.call_count, 2)
                self.assertEqual(result.get("feedId"), "123")

    def test_feed_adapter_create_feed_document(self):
        """Test FeedAdapter.create_feed_document calls backend correctly"""
        with self.backend.work_on("amazon.product.binding") as work:
            adapter = work.component(usage="feed.adapter")

            with mock.patch(
                "odoo.addons.connector_amazon_spapi.models.backend.AmazonBackend._call_sp_api",
                return_value={"feedDocumentId": "doc-123"},
            ) as mock_call:
                adapter.create_feed_document(content_type="text/xml; charset=UTF-8")

                mock_call.assert_called_once()
                call_args = mock_call.call_args
                self.assertEqual(call_args[0][0], "POST")
                self.assertIn("documents", call_args[0][1])

    def test_feed_adapter_get_feed(self):
        """Test FeedAdapter.get_feed calls backend correctly"""
        with self.backend.work_on("amazon.product.binding") as work:
            adapter = work.component(usage="feed.adapter")

            with mock.patch(
                "odoo.addons.connector_amazon_spapi.models.backend.AmazonBackend._call_sp_api",
                return_value={"feedId": "feed-123"},
            ) as mock_call:
                adapter.get_feed("feed-123")

                mock_call.assert_called_once()
                call_args = mock_call.call_args
                self.assertEqual(call_args[0][0], "GET")
                self.assertIn("feed-123", call_args[0][1])

    def test_catalog_adapter_search_catalog_items(self):
        """Test CatalogAdapter.search_catalog_items calls backend correctly"""
        with self.backend.work_on("amazon.product.binding") as work:
            adapter = work.component(usage="catalog.adapter")

            with mock.patch(
                "odoo.addons.connector_amazon_spapi.models.backend.AmazonBackend._call_sp_api",
                return_value={"items": []},
            ) as mock_call:
                adapter.search_catalog_items(
                    marketplace_id="ATVPDKIKX0DER", keywords="test product"
                )

                mock_call.assert_called_once()
                call_args = mock_call.call_args
                self.assertEqual(call_args[0][0], "GET")
                self.assertIn("catalog", call_args[0][1])
                self.assertIn("keywords", call_args[1]["params"])

    def test_catalog_adapter_get_catalog_item(self):
        """Test CatalogAdapter.get_catalog_item calls backend correctly"""
        with self.backend.work_on("amazon.product.binding") as work:
            adapter = work.component(usage="catalog.adapter")

            with mock.patch(
                "odoo.addons.connector_amazon_spapi.models.backend.AmazonBackend._call_sp_api",
                return_value={"asin": "B01ABCDEFG"},
            ) as mock_call:
                adapter.get_catalog_item(
                    asin="B01ABCDEFG", marketplace_id="ATVPDKIKX0DER"
                )

                mock_call.assert_called_once()
                call_args = mock_call.call_args
                self.assertEqual(call_args[0][0], "GET")
                self.assertIn("B01ABCDEFG", call_args[0][1])

    def test_listings_adapter_get_listings_item(self):
        """Test ListingsAdapter.get_listings_item calls backend correctly"""
        with self.backend.work_on("amazon.product.binding") as work:
            adapter = work.component(usage="listings.adapter")

            with mock.patch(
                "odoo.addons.connector_amazon_spapi.models.backend.AmazonBackend._call_sp_api",
                return_value={"sku": "TEST-SKU-001"},
            ) as mock_call:
                adapter.get_listings_item(
                    seller_sku="TEST-SKU-001", marketplace_ids=["ATVPDKIKX0DER"]
                )

                mock_call.assert_called_once()
                call_args = mock_call.call_args
                self.assertEqual(call_args[0][0], "GET")
                self.assertIn("TEST-SKU-001", call_args[0][1])

    def test_listings_adapter_put_listings_item(self):
        """Test ListingsAdapter.put_listings_item calls backend correctly"""
        with self.backend.work_on("amazon.product.binding") as work:
            adapter = work.component(usage="listings.adapter")

            with mock.patch(
                "odoo.addons.connector_amazon_spapi.models.backend.AmazonBackend._call_sp_api",
                return_value={"status": "ACCEPTED"},
            ) as mock_call:
                adapter.put_listings_item(
                    seller_sku="TEST-SKU-001",
                    marketplace_ids=["ATVPDKIKX0DER"],
                    product_type="PRODUCT",
                    attributes={},
                )

                mock_call.assert_called_once()
                call_args = mock_call.call_args
                self.assertEqual(call_args[0][0], "PUT")
                self.assertIn("TEST-SKU-001", call_args[0][1])


@tagged("post_install", "-at_install")
class TestShopAdapterIntegration(common.CommonConnectorAmazonSpapi):
    """Tests for shop model adapter integration"""

    @mock.patch(
        "odoo.addons.connector_amazon_spapi.components.backend_adapter."
        "AmazonOrdersAdapter.list_orders"
    )
    def test_sync_orders_uses_adapter(self, mock_list_orders):
        """Test sync_orders uses orders adapter instead of direct API call"""
        mock_list_orders.return_value = {"Orders": [], "NextToken": None}

        self.shop.sync_orders()

        # Should have called adapter method
        mock_list_orders.assert_called_once()
        call_args = mock_list_orders.call_args
        self.assertEqual(
            call_args[1]["marketplace_id"], self.marketplace.marketplace_id
        )


@tagged("post_install", "-at_install")
class TestOrderAdapterIntegration(common.CommonConnectorAmazonSpapi):
    """Tests for order model adapter integration"""

    def setUp(self):
        super().setUp()
        self.order = self._create_amazon_order()

    def _create_amazon_order(self, **kwargs):
        """Create a test Amazon order"""
        partner = self.env["res.partner"].create(
            {
                "name": "Test Amazon Customer",
                "email": "test@amazon.com",
            }
        )
        values = {
            "external_id": "111-1111111-1111111",
            "name": "111-1111111-1111111",
            "partner_id": partner.id,
            "shop_id": self.shop.id,
            "backend_id": self.backend.id,
            "status": "Pending",
            "purchase_date": "2025-12-19 10:00:00",
            "last_update_date": "2025-12-19 10:00:00",
            "state": "draft",
        }
        values.update(kwargs)
        return self.env["amazon.sale.order"].create(values)

    @mock.patch(
        "odoo.addons.connector_amazon_spapi.components.backend_adapter."
        "AmazonOrdersAdapter.get_order_items"
    )
    def test_sync_order_lines_uses_adapter(self, mock_get_order_items):
        """Test _sync_order_lines uses orders adapter"""
        mock_get_order_items.return_value = {"OrderItems": [], "NextToken": None}

        self.order._sync_order_lines()

        # Should have called adapter method
        mock_get_order_items.assert_called_once_with("111-1111111-1111111")
