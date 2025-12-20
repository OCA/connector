from odoo.addons.component.core import Component


class AmazonOrderImportMapper(Component):
    _name = "amazon.order.import.mapper"
    _inherit = "base.import.mapper"
    _usage = "import.mapper"
    _apply_on = ["amazon.sale.order"]

    # TODO: implement map_* methods for order fields, partner, shipping, taxes


class AmazonOrderLineImportMapper(Component):
    _name = "amazon.order.line.import.mapper"
    _inherit = "base.import.mapper"
    _usage = "import.mapper"
    _apply_on = ["amazon.sale.order.line"]

    # TODO: implement map_* methods for order lines


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
