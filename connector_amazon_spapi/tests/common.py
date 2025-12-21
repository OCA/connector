# Copyright 2025 Kencove
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html)

from datetime import datetime, timedelta

from odoo.addons.component.tests.common import TransactionComponentCase


class CommonConnectorAmazonSpapi(TransactionComponentCase):
    """Base class for Amazon SP-API connector tests"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))

    def setUp(self):
        super().setUp()
        self.backend = self._create_backend()
        self.marketplace = self._create_marketplace()
        self.shop = self._create_shop()
        # Create a simple product used by most sample Amazon items
        self.product = self.env["product.product"].create(
            {
                "name": "Test Product",
                "default_code": "TEST-SKU-001",
                "type": "service",
                "list_price": 99.99,
            }
        )

    def _create_backend(self, **kwargs):
        """Create a test backend record"""
        values = {
            "name": "Test Amazon Backend",
            "code": "test_amazon",
            "version": "spapi",
            "seller_id": "AKIAIOSFODNN7EXAMPLE",
            "region": "na",
            "lwa_client_id": "amzn1.application-oa2-client.test",
            "lwa_client_secret": "test-client-secret",
            "lwa_refresh_token": "Atzr|test-refresh-token",
            "company_id": self.env.company.id,
        }
        values.update(kwargs)
        return self.env["amazon.backend"].create(values)

    def _create_marketplace(self, **kwargs):
        """Create a test marketplace record"""
        # Get the default currency
        default_currency = self.env.company.currency_id

        values = {
            "name": "Amazon.com",
            "code": "US",
            "marketplace_id": "ATVPDKIKX0DER",
            "backend_id": self.backend.id,
            "currency_id": default_currency.id,
            "timezone": "America/New_York",
            "country_code": "US",
        }
        values.update(kwargs)
        return self.env["amazon.marketplace"].create(values)

    def _create_shop(self, **kwargs):
        """Create a test shop record"""
        values = {
            "name": "Test Amazon Shop",
            "backend_id": self.backend.id,
            "marketplace_id": self.marketplace.id,
            "company_id": self.env.company.id,
            "import_orders": True,
            "sync_stock": True,
            "sync_price": True,
        }
        values.update(kwargs)
        return self.env["amazon.shop"].create(values)

    def _create_sample_amazon_order(self):
        """Create a sample Amazon order data structure"""
        return {
            "AmazonOrderId": "111-1111111-1111111",
            "PurchaseDate": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "LastUpdateDate": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "OrderStatus": "Pending",
            "FulfillmentChannel": "MFN",
            "BuyerEmail": "test@example.com",
            "BuyerName": "Test Buyer",
            "BuyerPhoneNumber": "+1-555-0100",
            "ShipServiceLevel": "Standard",
            "IsBusinessOrder": False,
            "NumberOfItemsShipped": 1,
            "NumberOfItemsUnshipped": 0,
            "PaymentExecutionDetail": {"PaymentMethod": "Other"},
            "PaymentMethod": "Other",
            "OrderType": "StandardOrder",
            "EarliestShipDate": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "LatestShipDate": (datetime.now() + timedelta(days=5)).strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
            "IsISPU": False,
            "MarketplaceId": "ATVPDKIKX0DER",
            "ShippingAddress": {
                "AddressType": "Residential",
                "City": "Los Angeles",
                "County": "Los Angeles County",
                "District": "California",
                "Name": "Test Buyer",
                "Phone": "+1-555-0100",
                "PostalCode": "90210",
                "StateOrRegion": "CA",
                "Street1": "123 Test St",
                "CountryCode": "US",
            },
        }

    def _create_sample_amazon_order_item(self):
        """Create a sample Amazon order item data structure"""
        return {
            "OrderItemId": "TEST-ORDER-ITEM-001",
            "SellerSKU": "TEST-SKU-001",
            "ASIN": "TEST-ASIN-001",
            "Title": "Test Product",
            "QuantityOrdered": 1,
            "QuantityShipped": 0,
            "ItemPrice": {"Amount": "99.99", "CurrencyCode": "USD"},
            "ShippingPrice": {"Amount": "0.00", "CurrencyCode": "USD"},
            "ItemTax": {"Amount": "0.00", "CurrencyCode": "USD"},
            "ShippingTax": {"Amount": "0.00", "CurrencyCode": "USD"},
            "PromotionDiscount": {"Amount": "0.00", "CurrencyCode": "USD"},
            "SerialNumberRequired": False,
            "IsGift": False,
            "ConditionNote": "",
            "ConditionId": "New",
            "ConditionSubtypeId": "New",
            "DeemedReservePrice": {"Amount": "0.00", "CurrencyCode": "USD"},
            "IsFulfillable": True,
        }

    def _create_amazon_order(self, **kwargs):
        """Create an amazon.sale.order with required partner and sale.order"""
        # Create partner if not provided
        if "partner_id" not in kwargs:
            partner = self.env["res.partner"].create(
                {"name": "Test Buyer", "email": "test@example.com"}
            )
        else:
            partner = self.env["res.partner"].browse(kwargs.pop("partner_id"))

        # Create sale.order if odoo_id not provided
        if "odoo_id" not in kwargs:
            order_name = kwargs.get("name", "TEST-SALE-ORDER")
            sale_order = self.env["sale.order"].create(
                {
                    "partner_id": partner.id,
                    "name": order_name,
                }
            )
            kwargs["odoo_id"] = sale_order.id

        # Set default values if not provided
        defaults = {
            "shop_id": self.shop.id,
            "backend_id": self.backend.id,
            "external_id": "TEST-AMAZON-ORDER-001",
            "purchase_date": datetime.now(),
            "status": "Pending",
        }
        defaults.update(kwargs)

        return self.env["amazon.sale.order"].create(defaults)

    def _create_product_binding(self, **kwargs):
        """Create an amazon.product.binding"""
        defaults = {
            "backend_id": self.backend.id,
            "marketplace_id": self.marketplace.id,
            "odoo_id": self.product.id,
            "seller_sku": "TEST-SKU-001",
            "asin": "B08TEST123",
            "sync_stock": False,
            "sync_price": False,
        }
        defaults.update(kwargs)
        return self.env["amazon.product.binding"].create(defaults)

    def _create_sample_pricing_data(self, asin=None):
        """Create sample competitive pricing data from Amazon API"""
        return {
            "ASIN": asin or "B08TEST123",
            "status": "Success",
            "Product": {
                "CompetitivePricing": {
                    "CompetitivePrices": [
                        {
                            "CompetitivePriceId": "1",
                            "Price": {
                                "LandedPrice": {"CurrencyCode": "USD", "Amount": 99.99},
                                "ListingPrice": {
                                    "CurrencyCode": "USD",
                                    "Amount": 89.99,
                                },
                                "Shipping": {"CurrencyCode": "USD", "Amount": 10.00},
                            },
                            "condition": "New",
                            "subcondition": "New",
                            "belongsToRequester": True,
                        }
                    ],
                    "NumberOfOfferListings": [
                        {"condition": "New", "Count": 5},
                    ],
                },
            },
        }
