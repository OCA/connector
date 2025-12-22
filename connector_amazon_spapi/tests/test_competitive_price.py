# Copyright 2025 Kencove
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html)

from datetime import datetime
from unittest import mock

from odoo.exceptions import UserError
from odoo.tests import tagged

from . import common


@tagged("post_install", "-at_install")
class TestAmazonCompetitivePrice(common.CommonConnectorAmazonSpapi):
    """Tests for amazon.competitive.price model"""

    def setUp(self):
        super().setUp()
        self.product_binding = self._create_product_binding()

    def _create_product_binding(self, **kwargs):
        """Create a test product binding"""
        values = {
            "seller_sku": "TEST-SKU-001",
            "asin": "B01ABCDEFG",
            "backend_id": self.backend.id,
            "marketplace_id": self.marketplace.id,
            "odoo_id": self.product.id,
            "fulfillment_channel": "FBM",
            "sync_price": True,
            "sync_stock": True,
        }
        values.update(kwargs)
        return self.env["amazon.product.binding"].create(values)

    def _create_competitive_price(self, **kwargs):
        """Create a test competitive price record"""
        # Generate unique values to avoid constraint violations
        # Use timestamp-based approach for better uniqueness across test runs
        import uuid
        from time import time

        timestamp = int(time() * 1000000)  # microsecond precision
        unique_suffix = uuid.uuid4().hex[:8]

        # Only set defaults if not explicitly provided
        if "competitive_price_id" not in kwargs:
            kwargs["competitive_price_id"] = f"test-{timestamp}-{unique_suffix}"
        if "fetch_date" not in kwargs:
            kwargs["fetch_date"] = datetime.now()

        values = {
            "product_binding_id": self.product_binding.id,
            "asin": "B01ABCDEFG",
            "marketplace_id": self.marketplace.id,
            "listing_price": 89.99,
            "shipping_price": 5.00,
            "landed_price": 94.99,
            "currency_id": self.env.company.currency_id.id,
            "condition": "New",
            "offer_type": "BuyBox",
            "is_buy_box_winner": True,
            "number_of_offers_new": 5,
            "number_of_offers_used": 2,
        }
        values.update(kwargs)
        return self.env["amazon.competitive.price"].create(values)

    def _create_sample_pricing_api_response(self):
        """Create sample pricing API response"""
        return [
            {
                "ASIN": "B01ABCDEFG",
                "Product": {
                    "CompetitivePricing": {
                        "CompetitivePrices": [
                            {
                                "CompetitivePriceId": "1",
                                "Price": {
                                    "LandedPrice": {
                                        "CurrencyCode": "USD",
                                        "Amount": "94.99",
                                    },
                                    "ListingPrice": {
                                        "CurrencyCode": "USD",
                                        "Amount": "89.99",
                                    },
                                    "Shipping": {
                                        "CurrencyCode": "USD",
                                        "Amount": "5.00",
                                    },
                                },
                                "condition": "New",
                                "subcondition": "New",
                                "offerType": "BuyBox",
                                "belongsToRequester": False,
                            }
                        ],
                        "NumberOfOfferListings": [
                            {"condition": "New", "Count": 5},
                            {"condition": "Used", "Count": 2},
                        ],
                    }
                },
            }
        ]

    def test_competitive_price_creation(self):
        """Test creating a competitive price record"""
        comp_price = self._create_competitive_price()

        self.assertEqual(comp_price.asin, "B01ABCDEFG")
        self.assertEqual(comp_price.listing_price, 89.99)
        self.assertEqual(comp_price.shipping_price, 5.00)
        self.assertEqual(comp_price.landed_price, 94.99)
        self.assertTrue(comp_price.is_buy_box_winner)
        self.assertEqual(comp_price.number_of_offers_new, 5)

    def test_price_difference_computed(self):
        """Test price_difference field is computed correctly"""
        # Product list price is 99.99, competitive price is 89.99
        comp_price = self._create_competitive_price(listing_price=89.99)

        # Price difference should be 89.99 - 99.99 = -10.00
        self.assertEqual(comp_price.price_difference, -10.00)

    def test_our_current_price_computed(self):
        """Test our_current_price field shows product list price"""
        comp_price = self._create_competitive_price()

        self.assertAlmostEqual(
            comp_price.our_current_price, self.product.list_price, places=2
        )
        self.assertAlmostEqual(comp_price.our_current_price, 99.99, places=2)

    def test_action_apply_to_pricelist_no_pricelist(self):
        """Test apply to pricelist fails when no pricelist configured"""
        comp_price = self._create_competitive_price()

        result = comp_price.action_apply_to_pricelist()

        # Should return warning notification
        self.assertEqual(result["type"], "ir.actions.client")
        self.assertEqual(result["params"]["type"], "warning")

    def test_action_apply_to_pricelist_creates_item(self):
        """Test apply to pricelist creates pricelist item"""
        # Create pricelist for shop
        pricelist = self.env["product.pricelist"].create(
            {"name": "Amazon Pricelist", "currency_id": self.env.company.currency_id.id}
        )
        self.shop.write({"pricelist_id": pricelist.id})

        comp_price = self._create_competitive_price(listing_price=85.00)

        result = comp_price.action_apply_to_pricelist()

        # Should create pricelist item
        pricelist_item = self.env["product.pricelist.item"].search(
            [
                ("pricelist_id", "=", pricelist.id),
                ("product_id", "=", self.product.id),
            ]
        )
        self.assertTrue(pricelist_item)
        self.assertEqual(pricelist_item.fixed_price, 85.00)
        self.assertEqual(result["type"], "ir.actions.client")
        self.assertEqual(result["params"]["type"], "success")

    def test_action_apply_to_pricelist_updates_existing(self):
        """Test apply to pricelist updates existing pricelist item"""
        pricelist = self.env["product.pricelist"].create(
            {"name": "Amazon Pricelist", "currency_id": self.env.company.currency_id.id}
        )
        self.shop.write({"pricelist_id": pricelist.id})

        # Create existing pricelist item
        existing_item = self.env["product.pricelist.item"].create(
            {
                "pricelist_id": pricelist.id,
                "product_id": self.product.id,
                "fixed_price": 90.00,
                "compute_price": "fixed",
                "applied_on": "0_product_variant",
            }
        )

        comp_price = self._create_competitive_price(listing_price=85.00)
        comp_price.action_apply_to_pricelist()

        # Should update existing item, not create new one
        existing_item.invalidate_recordset()
        self.assertEqual(existing_item.fixed_price, 85.00)

        items = self.env["product.pricelist.item"].search(
            [
                ("pricelist_id", "=", pricelist.id),
                ("product_id", "=", self.product.id),
            ]
        )
        self.assertEqual(len(items), 1)

    def test_action_view_product(self):
        """Test action_view_product returns correct action"""
        comp_price = self._create_competitive_price()

        result = comp_price.action_view_product()

        self.assertEqual(result["type"], "ir.actions.act_window")
        self.assertEqual(result["res_model"], "product.product")
        self.assertEqual(result["res_id"], self.product.id)

    def test_archive_old_prices(self):
        """Test archive_old_prices method"""
        # Create old price (40 days ago)
        old_price = self._create_competitive_price(
            fetch_date=datetime.now().replace(year=2025, month=11, day=9)
        )

        # Create recent price
        recent_price = self._create_competitive_price()

        # Archive prices older than 30 days
        archived_count = self.env["amazon.competitive.price"].archive_old_prices(
            days=30
        )

        self.assertEqual(archived_count, 1)
        old_price.invalidate_recordset()
        self.assertFalse(old_price.active)
        self.assertTrue(recent_price.active)

    def test_unique_constraint(self):
        """Test unique constraint on competitive price"""
        import time

        from psycopg2 import IntegrityError

        # Create first record - capture its fetch_date for duplicate test
        first_record = self._create_competitive_price(
            competitive_price_id="test-id-unique-constraint-1"
        )
        test_fetch_date = first_record.fetch_date
        test_competitive_price_id = first_record.competitive_price_id

        # Try to create duplicate with exact same values - should raise IntegrityError
        # Ensure microsecond difference to avoid accidental duplicate
        # from datetime.now() between the two calls
        time.sleep(0.001)  # 1ms delay to ensure different timestamp in helper
        with self.assertRaises(IntegrityError):
            with self.env.cr.savepoint():
                self._create_competitive_price(
                    competitive_price_id=test_competitive_price_id,
                    fetch_date=test_fetch_date,
                )


@tagged("post_install", "-at_install")
class TestAmazonProductBindingCompetitivePricing(common.CommonConnectorAmazonSpapi):
    """Tests for product binding competitive pricing functionality"""

    def setUp(self):
        super().setUp()
        self.product_binding = self._create_product_binding()

    def _create_product_binding(self, **kwargs):
        """Create a test product binding"""
        import uuid

        values = {
            "seller_sku": kwargs.get("seller_sku", f"TEST-SKU-{uuid.uuid4().hex[:8]}"),
            "asin": "B01ABCDEFG",
            "backend_id": self.backend.id,
            "marketplace_id": self.marketplace.id,
            "odoo_id": self.product.id,
            "fulfillment_channel": "FBM",
        }
        values.update(kwargs)
        return self.env["amazon.product.binding"].create(values)

    def _create_sample_pricing_api_response(self):
        """Create sample pricing API response"""
        return [
            {
                "ASIN": "B01ABCDEFG",
                "Product": {
                    "CompetitivePricing": {
                        "CompetitivePrices": [
                            {
                                "CompetitivePriceId": "1",
                                "Price": {
                                    "LandedPrice": {
                                        "CurrencyCode": "USD",
                                        "Amount": "94.99",
                                    },
                                    "ListingPrice": {
                                        "CurrencyCode": "USD",
                                        "Amount": "89.99",
                                    },
                                    "Shipping": {
                                        "CurrencyCode": "USD",
                                        "Amount": "5.00",
                                    },
                                },
                                "condition": "New",
                                "subcondition": "New",
                                "offerType": "BuyBox",
                                "belongsToRequester": False,
                            }
                        ],
                        "NumberOfOfferListings": [
                            {"condition": "New", "Count": 5},
                            {"condition": "Used", "Count": 2},
                        ],
                    }
                },
            }
        ]

    def test_competitive_price_count_computed(self):
        """Test competitive_price_count field is computed"""
        self.assertEqual(self.product_binding.competitive_price_count, 0)

        # Create competitive prices
        self.env["amazon.competitive.price"].create(
            {
                "product_binding_id": self.product_binding.id,
                "asin": "B01ABCDEFG",
                "marketplace_id": self.marketplace.id,
                "listing_price": 89.99,
                "currency_id": self.env.company.currency_id.id,
            }
        )

        self.product_binding.invalidate_recordset()
        self.assertEqual(self.product_binding.competitive_price_count, 1)

    def test_action_fetch_competitive_prices_no_asin(self):
        """Test fetching prices fails when no ASIN"""
        binding_no_asin = self._create_product_binding(asin=False)

        with self.assertRaises(UserError) as context:
            binding_no_asin.action_fetch_competitive_prices()

        self.assertIn("no ASIN", str(context.exception))

    def test_action_fetch_competitive_prices_no_marketplace(self):
        """Test fetching prices fails when no marketplace"""
        binding_no_marketplace = self._create_product_binding(marketplace_id=False)

        with self.assertRaises(UserError) as context:
            binding_no_marketplace.action_fetch_competitive_prices()

        self.assertIn("No marketplace", str(context.exception))

    @mock.patch(
        "odoo.addons.connector_amazon_spapi.components.backend_adapter."
        "AmazonPricingAdapter.get_competitive_pricing"
    )
    def test_action_fetch_competitive_prices_success(
        self, mock_get_competitive_pricing
    ):
        """Test successfully fetching competitive prices"""
        mock_get_competitive_pricing.return_value = (
            self._create_sample_pricing_api_response()
        )

        result = self.product_binding.action_fetch_competitive_prices()

        # Should call adapter
        mock_get_competitive_pricing.assert_called_once_with(
            marketplace_id=self.marketplace.marketplace_id, asins=["B01ABCDEFG"]
        )

        # Should create competitive price record
        comp_prices = self.env["amazon.competitive.price"].search(
            [("product_binding_id", "=", self.product_binding.id)]
        )
        self.assertEqual(len(comp_prices), 1)
        self.assertEqual(comp_prices.listing_price, 89.99)
        self.assertEqual(comp_prices.shipping_price, 5.00)

        # Should return success notification
        self.assertEqual(result["type"], "ir.actions.client")
        self.assertEqual(result["params"]["type"], "success")

    @mock.patch(
        "odoo.addons.connector_amazon_spapi.components.backend_adapter."
        "AmazonPricingAdapter.get_competitive_pricing"
    )
    def test_action_fetch_competitive_prices_empty_response(
        self, mock_get_competitive_pricing
    ):
        """Test fetching prices with empty response"""
        mock_get_competitive_pricing.return_value = []

        with self.assertRaises(UserError) as context:
            self.product_binding.action_fetch_competitive_prices()

        self.assertIn("No competitive pricing data returned", str(context.exception))

    def test_action_view_competitive_prices(self):
        """Test action to view competitive prices"""
        result = self.product_binding.action_view_competitive_prices()

        self.assertEqual(result["type"], "ir.actions.act_window")
        self.assertEqual(result["res_model"], "amazon.competitive.price")
        self.assertIn(
            ("product_binding_id", "=", self.product_binding.id), result["domain"]
        )


@tagged("post_install", "-at_install")
class TestAmazonCompetitivePriceMapper(common.CommonConnectorAmazonSpapi):
    """Tests for competitive price mapper"""

    def setUp(self):
        super().setUp()
        self.product_binding = self._create_product_binding()

    def _create_product_binding(self, **kwargs):
        """Create a test product binding"""
        import uuid

        values = {
            "seller_sku": kwargs.get("seller_sku", f"TEST-SKU-{uuid.uuid4().hex[:8]}"),
            "asin": "B01ABCDEFG",
            "backend_id": self.backend.id,
            "marketplace_id": self.marketplace.id,
            "odoo_id": self.product.id,
        }
        values.update(kwargs)
        return self.env["amazon.product.binding"].create(values)

    def _get_mapper(self):
        """Get the competitive price mapper component"""
        with self.backend.work_on("amazon.product.binding") as work:
            return work.component(usage="import.mapper")

    def test_mapper_extracts_pricing_data(self):
        """Test mapper correctly extracts pricing data"""
        pricing_data = {
            "ASIN": "B01ABCDEFG",
            "Product": {
                "CompetitivePricing": {
                    "CompetitivePrices": [
                        {
                            "CompetitivePriceId": "1",
                            "Price": {
                                "LandedPrice": {
                                    "CurrencyCode": "USD",
                                    "Amount": "94.99",
                                },
                                "ListingPrice": {
                                    "CurrencyCode": "USD",
                                    "Amount": "89.99",
                                },
                                "Shipping": {"CurrencyCode": "USD", "Amount": "5.00"},
                            },
                            "condition": "New",
                            "subcondition": "New",
                            "offerType": "BuyBox",
                            "belongsToRequester": True,
                        }
                    ],
                    "NumberOfOfferListings": [
                        {"condition": "New", "Count": 5},
                        {"condition": "Used", "Count": 2},
                    ],
                }
            },
        }

        mapper = self._get_mapper()
        result = mapper.map_competitive_price(pricing_data, self.product_binding)

        self.assertEqual(result["asin"], "B01ABCDEFG")
        self.assertEqual(result["listing_price"], 89.99)
        self.assertEqual(result["shipping_price"], 5.00)
        self.assertEqual(result["landed_price"], 94.99)
        self.assertEqual(result["condition"], "New")
        self.assertEqual(result["subcondition"], "New")
        self.assertEqual(result["offer_type"], "BuyBox")
        self.assertTrue(result["is_featured_merchant"])
        self.assertTrue(result["is_buy_box_winner"])
        self.assertEqual(result["number_of_offers_new"], 5)
        self.assertEqual(result["number_of_offers_used"], 2)

    def test_mapper_handles_missing_competitive_prices(self):
        """Test mapper handles missing CompetitivePrices gracefully"""
        pricing_data = {
            "ASIN": "B01ABCDEFG",
            "Product": {"CompetitivePricing": {"CompetitivePrices": []}},
        }

        mapper = self._get_mapper()
        result = mapper.map_competitive_price(pricing_data, self.product_binding)

        self.assertIsNone(result)

    def test_mapper_handles_missing_offer_listings(self):
        """Test mapper handles missing NumberOfOfferListings"""
        pricing_data = {
            "ASIN": "B01ABCDEFG",
            "Product": {
                "CompetitivePricing": {
                    "CompetitivePrices": [
                        {
                            "CompetitivePriceId": "1",
                            "Price": {
                                "ListingPrice": {
                                    "CurrencyCode": "USD",
                                    "Amount": "89.99",
                                },
                                "LandedPrice": {
                                    "CurrencyCode": "USD",
                                    "Amount": "89.99",
                                },
                                "Shipping": {"CurrencyCode": "USD", "Amount": "0.00"},
                            },
                            "condition": "New",
                            "offerType": "Offer",
                        }
                    ],
                    "NumberOfOfferListings": [],
                }
            },
        }

        mapper = self._get_mapper()
        result = mapper.map_competitive_price(pricing_data, self.product_binding)

        self.assertIsNotNone(result)
        self.assertEqual(result["number_of_offers_new"], 0)
        self.assertEqual(result["number_of_offers_used"], 0)

    def test_mapper_sums_used_offers(self):
        """Test mapper correctly sums used/refurbished/collectible offers"""
        pricing_data = {
            "ASIN": "B01ABCDEFG",
            "Product": {
                "CompetitivePricing": {
                    "CompetitivePrices": [
                        {
                            "CompetitivePriceId": "1",
                            "Price": {
                                "ListingPrice": {
                                    "CurrencyCode": "USD",
                                    "Amount": "89.99",
                                },
                                "LandedPrice": {
                                    "CurrencyCode": "USD",
                                    "Amount": "89.99",
                                },
                                "Shipping": {"CurrencyCode": "USD", "Amount": "0.00"},
                            },
                            "condition": "New",
                            "offerType": "BuyBox",
                        }
                    ],
                    "NumberOfOfferListings": [
                        {"condition": "New", "Count": 10},
                        {"condition": "Used", "Count": 3},
                        {"condition": "Refurbished", "Count": 2},
                        {"condition": "Collectible", "Count": 1},
                    ],
                }
            },
        }

        mapper = self._get_mapper()
        result = mapper.map_competitive_price(pricing_data, self.product_binding)

        self.assertEqual(result["number_of_offers_new"], 10)
        # Used + Refurbished + Collectible = 3 + 2 + 1 = 6
        self.assertEqual(result["number_of_offers_used"], 6)
