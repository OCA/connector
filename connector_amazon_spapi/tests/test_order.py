# Copyright 2025 Kencove
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html)

from datetime import datetime, timedelta
from unittest import mock

from . import common


class TestAmazonOrder(common.CommonConnectorAmazonSpapi):
    """Tests for amazon.sale.order model"""

    def test_order_creation(self):
        """Test creating an order record"""
        order = self._create_amazon_order(
            external_id="111-1111111-1111111",
        )

        self.assertEqual(order.external_id, "111-1111111-1111111")
        self.assertEqual(order.shop_id, self.shop)
        self.assertEqual(order.backend_id, self.backend)

    @mock.patch(
        "odoo.addons.connector_amazon_spapi.models.backend.AmazonBackend._call_sp_api"
    )
    def test_create_order_from_amazon_data(self, mock_call_sp_api):
        """Test creating order from Amazon API data"""
        sample_order = self._create_sample_amazon_order()

        order_obj = self.env["amazon.sale.order"]
        order = order_obj._create_from_amazon_data(
            self.shop, self.backend, sample_order
        )

        self.assertEqual(order.external_id, sample_order["AmazonOrderId"])
        self.assertEqual(order.shop_id, self.shop)
        self.assertEqual(order.status, sample_order["OrderStatus"])

    def test_create_order_updates_existing(self):
        """Test creating order updates existing record"""
        sample_order = self._create_sample_amazon_order()

        # Create initial order
        existing_order = self._create_amazon_order(
            external_id=sample_order["AmazonOrderId"],
            purchase_date=sample_order["PurchaseDate"],
            status="Pending",
        )

        # Update with new data
        sample_order["OrderStatus"] = "Shipped"
        sample_order["LastUpdateDate"] = (
            datetime.now() + timedelta(hours=1)
        ).isoformat()

        order_obj = self.env["amazon.sale.order"]
        updated_order = order_obj._create_from_amazon_data(
            self.shop, self.backend, sample_order
        )

        self.assertEqual(updated_order.id, existing_order.id)
        self.assertEqual(updated_order.status, "Shipped")

    def test_create_order_updates_last_update_date(self):
        """Test order last_update_date is updated during sync"""
        order = self._create_amazon_order(
            external_id="111-1111111-1111111",
        )

        original_update = order.last_update_date
        order.write({"last_update_date": datetime.now()})
        self.assertNotEqual(order.last_update_date, original_update)

    @mock.patch(
        "odoo.addons.connector_amazon_spapi.models.backend.AmazonBackend._call_sp_api"
    )
    def test_sync_order_lines_fetches_from_api(self, mock_call_sp_api):
        """Test sync_order_lines fetches items from SP-API"""
        order = self._create_amazon_order(
            external_id="111-1111111-1111111",
            name="111-1111111-1111111",
            state="pending",
        )

        sample_item = self._create_sample_amazon_order_item()
        mock_call_sp_api.return_value = {
            "OrderItems": [sample_item],
            "NextToken": None,
        }

        order._sync_order_lines()

        mock_call_sp_api.assert_called_once()
        call_args = mock_call_sp_api.call_args
        self.assertIn(
            "/orders/v0/orders/111-1111111-1111111/orderitems", call_args[0][1]
        )

    @mock.patch(
        "odoo.addons.connector_amazon_spapi.models.backend.AmazonBackend._call_sp_api"
    )
    def test_create_order_line_from_amazon_data(self, mock_call_sp_api):
        """Test creating order line from Amazon API data"""
        order = self._create_amazon_order(
            external_id="111-1111111-1111111",
            name="111-1111111-1111111",
            state="pending",
        )

        sample_item = self._create_sample_amazon_order_item()

        line_obj = self.env["amazon.sale.order.line"]
        line = line_obj._create_from_amazon_data(order, sample_item)

        self.assertEqual(line.order_id, order)
        self.assertEqual(line.external_id, sample_item["OrderItemId"])
        self.assertEqual(line.product_title, sample_item["Title"])
        self.assertEqual(line.quantity, sample_item["QuantityOrdered"])

    def test_create_order_line_finds_product_by_sku(self):
        """Test create_order_line finds product by SKU"""
        # Create a product with matching SKU
        product = self.env["product.product"].create(
            {
                "name": "Test Amazon Product",
                "type": "product",
                "default_code": "SKU-123",
            }
        )

        order = self._create_amazon_order(
            external_id="111-1111111-1111111",
            name="111-1111111-1111111",
            state="pending",
        )

        sample_item = self._create_sample_amazon_order_item()
        sample_item["SellerSKU"] = "SKU-123"

        line_obj = self.env["amazon.sale.order.line"]
        line = line_obj._create_from_amazon_data(order, sample_item)

        self.assertEqual(line.product_id, product)

    def test_create_order_line_without_product(self):
        """Test create_order_line handles missing product"""
        order = self._create_amazon_order(
            external_id="111-1111111-1111111",
            name="111-1111111-1111111",
            state="pending",
        )

        sample_item = self._create_sample_amazon_order_item()
        sample_item["SellerSKU"] = "NON-EXISTENT-SKU"

        line_obj = self.env["amazon.sale.order.line"]
        line = line_obj._create_from_amazon_data(order, sample_item)

        # Should create line without product
        self.assertEqual(line.order_id, order)
        self.assertFalse(line.product_id)
        self.assertEqual(line.external_id, sample_item["OrderItemId"])

    def test_order_line_quantity_and_pricing(self):
        """Test order line quantity and pricing are correct"""
        order = self._create_amazon_order(
            external_id="111-1111111-1111111",
            name="111-1111111-1111111",
            state="pending",
        )

        sample_item = self._create_sample_amazon_order_item()

        line_obj = self.env["amazon.sale.order.line"]
        line = line_obj._create_from_amazon_data(order, sample_item)

        # Verify quantity
        self.assertEqual(line.quantity, sample_item["QuantityOrdered"])
        self.assertEqual(line.quantity_shipped, sample_item["QuantityShipped"])

        # Verify pricing (converted from string to float)
        item_price = float(sample_item["ItemPrice"]["Amount"])
        self.assertEqual(float(line.price_unit), item_price)

    @mock.patch(
        "odoo.addons.connector_amazon_spapi.models.backend.AmazonBackend._call_sp_api"
    )
    def test_sync_order_lines_pagination(self, mock_call_sp_api):
        """Test sync_order_lines handles pagination"""
        order = self._create_amazon_order(
            external_id="111-1111111-1111111",
            name="111-1111111-1111111",
            state="pending",
        )

        item1 = self._create_sample_amazon_order_item()
        item1["OrderItemId"] = "001"

        item2 = self._create_sample_amazon_order_item()
        item2["OrderItemId"] = "002"

        # First call returns NextToken
        mock_call_sp_api.side_effect = [
            {"OrderItems": [item1], "NextToken": "token123"},
            {"OrderItems": [item2], "NextToken": None},
        ]

        order._sync_order_lines()

        self.assertEqual(mock_call_sp_api.call_count, 2)
        lines = self.env["amazon.sale.order.line"].search([("order_id", "=", order.id)])
        self.assertEqual(len(lines), 2)

    def test_order_line_creation_with_all_fields(self):
        """Test order line stores all relevant Amazon fields"""
        order = self._create_amazon_order(
            external_id="111-1111111-1111111",
            name="111-1111111-1111111",
            state="pending",
        )

        sample_item = self._create_sample_amazon_order_item()

        line_obj = self.env["amazon.sale.order.line"]
        line = line_obj._create_from_amazon_data(order, sample_item)

        # Verify all important fields are stored
        self.assertEqual(line.external_id, sample_item["OrderItemId"])
        self.assertEqual(line.asin, sample_item["ASIN"])
        self.assertEqual(line.seller_sku, sample_item["SellerSKU"])
        self.assertEqual(line.product_title, sample_item["Title"])
        self.assertEqual(line.quantity, sample_item["QuantityOrdered"])
        self.assertEqual(line.quantity_shipped, sample_item["QuantityShipped"])

    @mock.patch(
        "odoo.addons.connector_amazon_spapi.models.backend.AmazonBackend._call_sp_api"
    )
    def test_order_with_no_lines_no_sync_error(self, mock_call_sp_api):
        """Test syncing order with no lines doesn't cause error"""
        order = self._create_amazon_order(
            external_id="111-1111111-1111111",
            name="111-1111111-1111111",
            state="pending",
        )

        mock_call_sp_api.return_value = {
            "OrderItems": [],
            "NextToken": None,
        }

        order._sync_order_lines()

        lines = self.env["amazon.sale.order.line"].search([("order_id", "=", order.id)])
        self.assertEqual(len(lines), 0)

    def test_order_fields_match_amazon_order_data(self):
        """Test order record contains fields from Amazon order data"""
        sample_order = self._create_sample_amazon_order()

        order = self._create_amazon_order(
            external_id=sample_order["AmazonOrderId"],
            name=sample_order["AmazonOrderId"],
            state="pending",
            status=sample_order["OrderStatus"],
            buyer_email=sample_order.get("BuyerEmail"),
            buyer_name=sample_order["ShippingAddress"]["Name"],
        )

        self.assertEqual(order.external_id, sample_order["AmazonOrderId"])
        self.assertEqual(order.status, sample_order["OrderStatus"])
        self.assertEqual(order.buyer_email, sample_order.get("BuyerEmail"))
