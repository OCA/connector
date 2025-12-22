# Copyright 2025 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)


from .common import CommonConnectorAmazonSpapi


class TestAmazonOrderImportMapper(CommonConnectorAmazonSpapi):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.mapper = cls.env["amazon.order.import.mapper"]

    def test_map_buyer_phone_present(self):
        """Test that buyer phone number is mapped when present"""
        record = {"BuyerPhoneNumber": "+1-555-1234"}

        mapper_instance = self.mapper.with_context(
            amazon_backend_id=self.backend.id
        ).work_on(model_name="amazon.sale.order")
        result = mapper_instance.map_buyer_phone(record)

        self.assertEqual(result, {"buyer_phone": "+1-555-1234"})

    def test_map_buyer_phone_missing(self):
        """Test that empty dict is returned when phone is missing"""
        record = {}

        mapper_instance = self.mapper.with_context(
            amazon_backend_id=self.backend.id
        ).work_on(model_name="amazon.sale.order")
        result = mapper_instance.map_buyer_phone(record)

        self.assertEqual(result, {})

    def test_map_backend_and_shop_requires_shop(self):
        """Test that ValueError is raised when shop is missing"""
        record = {}

        mapper_instance = self.mapper.with_context(
            amazon_backend_id=self.backend.id
        ).work_on(model_name="amazon.sale.order")
        mapper_instance.options = {}

        with self.assertRaises(ValueError) as cm:
            mapper_instance.map_backend_and_shop(record)

        self.assertIn("Shop is required", str(cm.exception))

    def test_map_backend_and_shop_success(self):
        """Test that backend and shop are correctly mapped"""
        record = {}

        mapper_instance = self.mapper.with_context(
            amazon_backend_id=self.backend.id
        ).work_on(model_name="amazon.sale.order")
        mapper_instance.options = {"shop": self.shop}

        result = mapper_instance.map_backend_and_shop(record)

        self.assertEqual(result["backend_id"], self.shop.backend_id.id)
        self.assertEqual(result["shop_id"], self.shop.id)

    def test_map_marketplace_matches_shop_marketplace(self):
        """Test that marketplace is mapped when it matches shop's marketplace"""
        record = {"MarketplaceId": self.marketplace.marketplace_id}

        mapper_instance = self.mapper.with_context(
            amazon_backend_id=self.backend.id
        ).work_on(model_name="amazon.sale.order")
        mapper_instance.options = {"shop": self.shop}

        result = mapper_instance.map_marketplace(record)

        self.assertEqual(result["marketplace_id"], self.marketplace.id)

    def test_map_marketplace_missing_in_record(self):
        """Test that empty dict is returned when marketplace is missing"""
        record = {}

        mapper_instance = self.mapper.with_context(
            amazon_backend_id=self.backend.id
        ).work_on(model_name="amazon.sale.order")
        mapper_instance.options = {"shop": self.shop}

        result = mapper_instance.map_marketplace(record)

        self.assertEqual(result, {})

    def test_map_partner_creates_new_partner(self):
        """Test that new partner is created when email not found"""
        record = {
            "BuyerName": "John Doe",
            "BuyerEmail": "newcustomer@example.com",
            "BuyerPhoneNumber": "+1-555-9999",
            "ShippingAddress": {
                "Name": "John Doe",
                "Street1": "123 Main St",
                "Street2": "Apt 4",
                "City": "New York",
                "StateOrRegion": "NY",
                "PostalCode": "10001",
                "CountryCode": "US",
                "Phone": "+1-555-9999",
            },
        }

        mapper_instance = self.mapper.with_context(
            amazon_backend_id=self.backend.id
        ).work_on(model_name="amazon.sale.order")

        result = mapper_instance.map_partner(record)

        partner = self.env["res.partner"].browse(result["partner_id"])
        self.assertEqual(partner.name, "John Doe")
        self.assertEqual(partner.email, "newcustomer@example.com")
        self.assertEqual(partner.phone, "+1-555-9999")
        self.assertEqual(partner.street, "123 Main St")
        self.assertEqual(partner.street2, "Apt 4")
        self.assertEqual(partner.city, "New York")
        self.assertEqual(partner.zip, "10001")
        self.assertEqual(partner.country_id.code, "US")

    def test_map_partner_finds_existing_by_email(self):
        """Test that existing partner is found by email"""
        existing_partner = self.env["res.partner"].create(
            {
                "name": "Existing Customer",
                "email": "existing@example.com",
            }
        )

        record = {
            "BuyerName": "John Doe",
            "BuyerEmail": "existing@example.com",
            "ShippingAddress": {},
        }

        mapper_instance = self.mapper.with_context(
            amazon_backend_id=self.backend.id
        ).work_on(model_name="amazon.sale.order")

        result = mapper_instance.map_partner(record)

        self.assertEqual(result["partner_id"], existing_partner.id)

    def test_get_state_id_resolves_us_state(self):
        """Test that US state is correctly resolved"""
        mapper_instance = self.mapper.with_context(
            amazon_backend_id=self.backend.id
        ).work_on(model_name="amazon.sale.order")

        state_id = mapper_instance._get_state_id("NY", "US")

        self.assertTrue(state_id)
        state = self.env["res.country.state"].browse(state_id)
        self.assertEqual(state.code, "NY")
        self.assertEqual(state.country_id.code, "US")

    def test_get_state_id_missing_inputs(self):
        """Test that False is returned when state or country is missing"""
        mapper_instance = self.mapper.with_context(
            amazon_backend_id=self.backend.id
        ).work_on(model_name="amazon.sale.order")

        result = mapper_instance._get_state_id(None, "US")
        self.assertFalse(result)

        result = mapper_instance._get_state_id("NY", None)
        self.assertFalse(result)

    def test_get_country_id_resolves_us(self):
        """Test that US country is correctly resolved"""
        mapper_instance = self.mapper.with_context(
            amazon_backend_id=self.backend.id
        ).work_on(model_name="amazon.sale.order")

        country_id = mapper_instance._get_country_id("US")

        self.assertTrue(country_id)
        country = self.env["res.country"].browse(country_id)
        self.assertEqual(country.code, "US")

    def test_get_country_id_missing_input(self):
        """Test that False is returned when country code is missing"""
        mapper_instance = self.mapper.with_context(
            amazon_backend_id=self.backend.id
        ).work_on(model_name="amazon.sale.order")

        result = mapper_instance._get_country_id(None)
        self.assertFalse(result)


class TestAmazonOrderLineImportMapper(CommonConnectorAmazonSpapi):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.mapper = cls.env["amazon.order.line.import.mapper"]

    def test_map_quantities_parses_integers(self):
        """Test that integer quantities are correctly parsed"""
        record = {
            "QuantityOrdered": "3",
            "QuantityShipped": "2",
        }

        mapper_instance = self.mapper.with_context(
            amazon_backend_id=self.backend.id
        ).work_on(model_name="amazon.sale.order.line")

        result = mapper_instance.map_quantities(record)

        self.assertEqual(result["quantity"], 3.0)
        self.assertEqual(result["quantity_shipped"], 2.0)

    def test_map_quantities_handles_missing_values(self):
        """Test that missing quantities default to 0"""
        record = {}

        mapper_instance = self.mapper.with_context(
            amazon_backend_id=self.backend.id
        ).work_on(model_name="amazon.sale.order.line")

        result = mapper_instance.map_quantities(record)

        self.assertEqual(result["quantity"], 0.0)
        self.assertEqual(result["quantity_shipped"], 0.0)

    def test_map_quantities_handles_invalid_values(self):
        """Test that invalid quantities default to 0"""
        record = {
            "QuantityOrdered": "invalid",
            "QuantityShipped": None,
        }

        mapper_instance = self.mapper.with_context(
            amazon_backend_id=self.backend.id
        ).work_on(model_name="amazon.sale.order.line")

        result = mapper_instance.map_quantities(record)

        self.assertEqual(result["quantity"], 0.0)
        self.assertEqual(result["quantity_shipped"], 0.0)

    def test_map_order_requires_amazon_order(self):
        """Test that ValueError is raised when amazon_order is missing"""
        record = {}

        mapper_instance = self.mapper.with_context(
            amazon_backend_id=self.backend.id
        ).work_on(model_name="amazon.sale.order.line")
        mapper_instance.options = {}

        with self.assertRaises(ValueError) as cm:
            mapper_instance.map_order(record)

        self.assertIn("Amazon order is required", str(cm.exception))

    def test_map_order_success(self):
        """Test that amazon order is correctly mapped"""
        amazon_order = self.env["amazon.sale.order"].create(
            {
                "backend_id": self.backend.id,
                "shop_id": self.shop.id,
                "external_id": "TEST-ORDER-1",
            }
        )

        record = {}

        mapper_instance = self.mapper.with_context(
            amazon_backend_id=self.backend.id
        ).work_on(model_name="amazon.sale.order.line")
        mapper_instance.options = {"amazon_order": amazon_order}

        result = mapper_instance.map_order(record)

        self.assertEqual(result["amazon_order_id"], amazon_order.id)
        self.assertEqual(result["backend_id"], self.backend.id)


class TestAmazonProductPriceImportMapper(CommonConnectorAmazonSpapi):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.mapper = cls.env["amazon.product.price.import.mapper"]

    def test_map_competitive_price_extracts_buy_box_price(self):
        """Test that Buy Box competitive price is correctly extracted"""
        product_binding = self.env["amazon.product.binding"].create(
            {
                "backend_id": self.backend.id,
                "marketplace_id": self.marketplace.id,
                "external_id": "TEST-PRODUCT-1",
            }
        )

        pricing_data = {
            "ASIN": "B08N5WRWNW",
            "Product": {
                "CompetitivePricing": {
                    "CompetitivePrices": [
                        {
                            "CompetitivePriceId": "1",
                            "condition": "New",
                            "subcondition": "New",
                            "offerType": "BuyBox",
                            "belongsToRequester": True,
                            "Price": {
                                "LandedPrice": {
                                    "CurrencyCode": "USD",
                                    "Amount": "29.99",
                                },
                                "ListingPrice": {
                                    "CurrencyCode": "USD",
                                    "Amount": "24.99",
                                },
                                "Shipping": {
                                    "CurrencyCode": "USD",
                                    "Amount": "5.00",
                                },
                            },
                        }
                    ],
                    "NumberOfOfferListings": [
                        {"condition": "New", "Count": 5},
                        {"condition": "Used", "Count": 2},
                    ],
                }
            },
        }

        mapper_instance = self.mapper.with_context(
            amazon_backend_id=self.backend.id
        ).work_on(model_name="amazon.product.binding")

        result = mapper_instance.map_competitive_price(pricing_data, product_binding)

        self.assertEqual(result["asin"], "B08N5WRWNW")
        self.assertEqual(result["product_binding_id"], product_binding.id)
        self.assertEqual(result["marketplace_id"], self.marketplace.id)
        self.assertEqual(result["competitive_price_id"], "1")
        self.assertEqual(result["landed_price"], 29.99)
        self.assertEqual(result["listing_price"], 24.99)
        self.assertEqual(result["shipping_price"], 5.00)
        self.assertEqual(result["condition"], "New")
        self.assertEqual(result["subcondition"], "New")
        self.assertEqual(result["offer_type"], "BuyBox")
        self.assertEqual(result["number_of_offers_new"], 5)
        self.assertEqual(result["number_of_offers_used"], 2)
        self.assertTrue(result["is_buy_box_winner"])
        self.assertTrue(result["is_featured_merchant"])

    def test_map_competitive_price_returns_none_without_prices(self):
        """Test that None is returned when no competitive prices exist"""
        product_binding = self.env["amazon.product.binding"].create(
            {
                "backend_id": self.backend.id,
                "marketplace_id": self.marketplace.id,
                "external_id": "TEST-PRODUCT-2",
            }
        )

        pricing_data = {
            "ASIN": "B08N5WRWNW",
            "Product": {
                "CompetitivePricing": {
                    "CompetitivePrices": [],
                }
            },
        }

        mapper_instance = self.mapper.with_context(
            amazon_backend_id=self.backend.id
        ).work_on(model_name="amazon.product.binding")

        result = mapper_instance.map_competitive_price(pricing_data, product_binding)

        self.assertIsNone(result)

    def test_map_competitive_price_defaults_currency_to_usd(self):
        """Test that currency defaults to USD when not specified"""
        product_binding = self.env["amazon.product.binding"].create(
            {
                "backend_id": self.backend.id,
                "marketplace_id": self.marketplace.id,
                "external_id": "TEST-PRODUCT-3",
            }
        )

        pricing_data = {
            "ASIN": "B08N5WRWNW",
            "Product": {
                "CompetitivePricing": {
                    "CompetitivePrices": [
                        {
                            "CompetitivePriceId": "1",
                            "Price": {
                                "ListingPrice": {"Amount": "19.99"},
                            },
                        }
                    ],
                }
            },
        }

        mapper_instance = self.mapper.with_context(
            amazon_backend_id=self.backend.id
        ).work_on(model_name="amazon.product.binding")

        result = mapper_instance.map_competitive_price(pricing_data, product_binding)

        currency = self.env["res.currency"].browse(result["currency_id"])
        self.assertEqual(currency.name, "USD")

    def test_map_competitive_price_handles_multiple_used_conditions(self):
        """Test that multiple used condition counts are aggregated"""
        product_binding = self.env["amazon.product.binding"].create(
            {
                "backend_id": self.backend.id,
                "marketplace_id": self.marketplace.id,
                "external_id": "TEST-PRODUCT-4",
            }
        )

        pricing_data = {
            "ASIN": "B08N5WRWNW",
            "Product": {
                "CompetitivePricing": {
                    "CompetitivePrices": [
                        {
                            "CompetitivePriceId": "1",
                            "Price": {
                                "ListingPrice": {
                                    "CurrencyCode": "USD",
                                    "Amount": "14.99",
                                }
                            },
                        }
                    ],
                    "NumberOfOfferListings": [
                        {"condition": "New", "Count": 3},
                        {"condition": "Used", "Count": 4},
                        {"condition": "Refurbished", "Count": 2},
                        {"condition": "Collectible", "Count": 1},
                    ],
                }
            },
        }

        mapper_instance = self.mapper.with_context(
            amazon_backend_id=self.backend.id
        ).work_on(model_name="amazon.product.binding")

        result = mapper_instance.map_competitive_price(pricing_data, product_binding)

        self.assertEqual(result["number_of_offers_new"], 3)
        # Should sum Used + Refurbished + Collectible = 4 + 2 + 1 = 7
        self.assertEqual(result["number_of_offers_used"], 7)

    def test_map_competitive_price_non_buy_box_offer(self):
        """Test that is_buy_box_winner is False for regular offers"""
        product_binding = self.env["amazon.product.binding"].create(
            {
                "backend_id": self.backend.id,
                "marketplace_id": self.marketplace.id,
                "external_id": "TEST-PRODUCT-5",
            }
        )

        pricing_data = {
            "ASIN": "B08N5WRWNW",
            "Product": {
                "CompetitivePricing": {
                    "CompetitivePrices": [
                        {
                            "CompetitivePriceId": "2",
                            "offerType": "Offer",  # Not BuyBox
                            "belongsToRequester": False,
                            "Price": {
                                "ListingPrice": {
                                    "CurrencyCode": "USD",
                                    "Amount": "19.99",
                                }
                            },
                        }
                    ],
                }
            },
        }

        mapper_instance = self.mapper.with_context(
            amazon_backend_id=self.backend.id
        ).work_on(model_name="amazon.product.binding")

        result = mapper_instance.map_competitive_price(pricing_data, product_binding)

        self.assertFalse(result["is_buy_box_winner"])
        self.assertFalse(result["is_featured_merchant"])
