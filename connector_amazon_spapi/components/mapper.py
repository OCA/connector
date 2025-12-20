from odoo import _

from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import mapping


class AmazonOrderImportMapper(Component):
    _name = "amazon.order.import.mapper"
    _inherit = "base.import.mapper"
    _usage = "import.mapper"
    _apply_on = ["amazon.sale.order"]

    direct = [
        ("AmazonOrderId", "external_id"),
        ("PurchaseDate", "purchase_date"),
        ("LastUpdateDate", "last_update_date"),
        ("OrderStatus", "status"),
        ("FulfillmentChannel", "fulfillment_channel"),
        ("BuyerEmail", "buyer_email"),
        ("BuyerName", "buyer_name"),
    ]

    @mapping
    def map_buyer_phone(self, record):
        """Map buyer phone number"""
        phone = record.get("BuyerPhoneNumber")
        if phone:
            return {"buyer_phone": phone}
        return {}

    @mapping
    def map_backend_and_shop(self, record):
        """Map backend and shop references from context"""
        shop = self.options.get("shop")
        if not shop:
            raise ValueError(_("Shop is required to import orders"))

        return {
            "backend_id": shop.backend_id.id,
            "shop_id": shop.id,
        }

    @mapping
    def map_marketplace(self, record):
        """Map marketplace from record"""
        marketplace_id = record.get("MarketplaceId")
        if not marketplace_id:
            return {}

        shop = self.options.get("shop")
        if shop and shop.marketplace_id.marketplace_id == marketplace_id:
            return {"marketplace_id": shop.marketplace_id.id}

        # Search for marketplace if not matching shop's marketplace
        marketplace = self.env["amazon.marketplace"].search(
            [
                ("marketplace_id", "=", marketplace_id),
                ("backend_id", "=", shop.backend_id.id),
            ],
            limit=1,
        )
        if marketplace:
            return {"marketplace_id": marketplace.id}
        return {}

    @mapping
    def map_partner(self, record):
        """Map or create customer partner from shipping address"""
        shipping_address = record.get("ShippingAddress", {})
        buyer_name = record.get("BuyerName") or shipping_address.get(
            "Name", "Amazon Customer"
        )
        buyer_email = record.get("BuyerEmail")

        # Try to find existing partner by email
        partner = None
        if buyer_email:
            partner = self.env["res.partner"].search(
                [("email", "=", buyer_email)], limit=1
            )

        # Create new partner if not found
        if not partner:
            partner_vals = {
                "name": buyer_name,
                "email": buyer_email or False,
                "phone": record.get("BuyerPhoneNumber")
                or shipping_address.get("Phone", False),
                "street": shipping_address.get("Street1"),
                "street2": shipping_address.get("Street2"),
                "city": shipping_address.get("City"),
                "state_id": self._get_state_id(
                    shipping_address.get("StateOrRegion"),
                    shipping_address.get("CountryCode"),
                ),
                "zip": shipping_address.get("PostalCode"),
                "country_id": self._get_country_id(shipping_address.get("CountryCode")),
            }
            partner = self.env["res.partner"].create(partner_vals)

        return {"partner_id": partner.id}

    def _get_state_id(self, state_code, country_code):
        """Get state ID from code and country"""
        if not state_code or not country_code:
            return False

        country = self._get_country_id(country_code)
        if not country:
            return False

        state = self.env["res.country.state"].search(
            [
                ("code", "=", state_code),
                ("country_id", "=", country),
            ],
            limit=1,
        )
        return state.id if state else False

    def _get_country_id(self, country_code):
        """Get country ID from ISO code"""
        if not country_code:
            return False

        country = self.env["res.country"].search([("code", "=", country_code)], limit=1)
        return country.id if country else False


class AmazonOrderLineImportMapper(Component):
    _name = "amazon.order.line.import.mapper"
    _inherit = "base.import.mapper"
    _usage = "import.mapper"
    _apply_on = ["amazon.sale.order.line"]

    direct = [
        ("OrderItemId", "external_id"),
        ("SellerSKU", "seller_sku"),
        ("ASIN", "asin"),
        ("Title", "product_title"),
    ]

    @mapping
    def map_quantities(self, record):
        """Map ordered and shipped quantities"""
        try:
            quantity = float(record.get("QuantityOrdered", 0))
        except (ValueError, TypeError):
            quantity = 0.0

        try:
            quantity_shipped = float(record.get("QuantityShipped", 0))
        except (ValueError, TypeError):
            quantity_shipped = 0.0

        return {
            "quantity": quantity,
            "quantity_shipped": quantity_shipped,
        }

    @mapping
    def map_order(self, record):
        """Map Amazon order reference from context"""
        amazon_order = self.options.get("amazon_order")
        if not amazon_order:
            raise ValueError(_("Amazon order is required to import order lines"))

        return {
            "amazon_order_id": amazon_order.id,
            "backend_id": amazon_order.backend_id.id,
        }


class AmazonProductPriceImportMapper(Component):
    _name = "amazon.product.price.import.mapper"
    _inherit = "base.import.mapper"
    _usage = "import.mapper"
    _apply_on = ["amazon.product.binding"]

    def map_competitive_price(self, pricing_data, product_binding):
        """Map Amazon Pricing API response to competitive price record

        Args:
            pricing_data: Single product pricing data from API response
            product_binding: amazon.product.binding record

        Returns:
            dict: Values for amazon.competitive.price creation
        """
        product_data = pricing_data.get("Product", {})
        competitive_pricing = product_data.get("CompetitivePricing", {})
        competitive_prices = competitive_pricing.get("CompetitivePrices", [])

        if not competitive_prices:
            return None

        # Get the first (usually Buy Box) competitive price
        comp_price = competitive_prices[0]
        price_info = comp_price.get("Price", {})

        # Extract price components
        landed_price_data = price_info.get("LandedPrice", {})
        listing_price_data = price_info.get("ListingPrice", {})
        shipping_data = price_info.get("Shipping", {})

        # Get currency
        currency_code = listing_price_data.get("CurrencyCode", "USD")  # Default to USD
        currency = self.env["res.currency"].search(
            [("name", "=", currency_code)], limit=1
        )
        if not currency:
            currency = self.env.company.currency_id

        # Get offer counts
        offer_listings = competitive_pricing.get("NumberOfOfferListings", [])
        num_new_offers = 0
        num_used_offers = 0
        for offer_count in offer_listings:
            condition = offer_count.get("condition", "")
            count = offer_count.get("Count", 0)
            if condition == "New":
                num_new_offers = count
            elif condition in ["Used", "Refurbished", "Collectible"]:
                num_used_offers += count

        return {
            "product_binding_id": product_binding.id,
            "asin": pricing_data.get("ASIN"),
            "marketplace_id": product_binding.marketplace_id.id,
            "competitive_price_id": comp_price.get("CompetitivePriceId"),
            "landed_price": float(landed_price_data.get("Amount", 0)),
            "listing_price": float(listing_price_data.get("Amount", 0)),
            "shipping_price": float(shipping_data.get("Amount", 0)),
            "currency_id": currency.id,
            "condition": comp_price.get("condition", "New"),
            "subcondition": comp_price.get("subcondition"),
            "offer_type": comp_price.get("offerType", "Offer"),
            "number_of_offers_new": num_new_offers,
            "number_of_offers_used": num_used_offers,
            "is_buy_box_winner": comp_price.get("offerType") == "BuyBox",
            "is_featured_merchant": comp_price.get("belongsToRequester", False),
        }
