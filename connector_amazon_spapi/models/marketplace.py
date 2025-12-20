from odoo import api, fields, models


class AmazonMarketplace(models.Model):
    _name = "amazon.marketplace"
    _description = "Amazon Marketplace"

    name = fields.Char(required=True)
    code = fields.Char(required=True, help="Internal code, e.g., US, CA, UK.")
    marketplace_id = fields.Char(
        required=True,
        string="Marketplace ID",
        help="Identifier used by the SP-API for this marketplace.",
    )
    region = fields.Char(
        help="Optional Amazon region identifier (e.g., EU, US, FarEast)",
    )
    backend_id = fields.Many2one(
        comodel_name="amazon.backend",
        required=True,
        ondelete="cascade",
    )
    currency_id = fields.Many2one(comodel_name="res.currency", required=True)
    timezone = fields.Char()
    country_code = fields.Char()
    order_status_filter = fields.Char(
        default="Unshipped,PartiallyShipped",
        help="Comma-separated statuses to pull.",
    )
    fulfillment_channel_filter = fields.Char(
        string="Fulfillment Channels",
        default="AFN,MFN",
        help="Comma-separated channels (AFN/AFS/DEFAULT/MFN).",
    )

    # Delivery method mappings (optional - delivery module not required)
    delivery_standard_id = fields.Many2one(
        comodel_name="delivery.carrier",
        string="Standard Shipping",
        help="Odoo delivery method for Amazon Standard shipping.",
        ondelete="set null",
    )
    delivery_expedited_id = fields.Many2one(
        comodel_name="delivery.carrier",
        string="Expedited Shipping",
        help="Odoo delivery method for Amazon Expedited shipping.",
        ondelete="set null",
    )
    delivery_priority_id = fields.Many2one(
        comodel_name="delivery.carrier",
        string="Priority Shipping",
        help="Odoo delivery method for Amazon Priority/NextDay shipping.",
        ondelete="set null",
    )
    delivery_scheduled_id = fields.Many2one(
        comodel_name="delivery.carrier",
        string="Scheduled Delivery",
        help="Odoo delivery method for Amazon Scheduled delivery.",
        ondelete="set null",
    )
    delivery_default_id = fields.Many2one(
        comodel_name="delivery.carrier",
        string="Default Carrier",
        help="Fallback delivery method when Amazon shipping level is unknown.",
        ondelete="set null",
    )

    active = fields.Boolean(default=True)

    @api.model
    def create(self, vals):
        """Ensure a non-null currency_id on creation.

        Fallback order:
        - Backend company currency
        - Heuristic by marketplace code/name/region (GBP for UK, EUR for EU, USD for NA, JPY for JP)
        - Current company currency
        - Any available currency
        """
        # Ensure code is provided for the not-null constraint
        if not vals.get("code"):
            # Prefer explicit country_code
            country_code = (vals.get("country_code") or "").upper()
            if country_code:
                vals["code"] = country_code
            else:
                name_hint = vals.get("name") or ""
                vals["code"] = (
                    name_hint[:2].upper() or (vals.get("marketplace_id") or "MK")[:2]
                )

        if not vals.get("currency_id"):
            Currency = self.env["res.currency"]
            currency = False

            backend_id = vals.get("backend_id")
            backend = None
            if backend_id:
                backend = self.env["amazon.backend"].browse(backend_id)
                if backend and backend.company_id and backend.company_id.currency_id:
                    currency = backend.company_id.currency_id

            # Heuristic mapping if still empty
            if not currency:
                code = (vals.get("code") or "").upper()
                name = (vals.get("name") or "").lower()
                region = (
                    vals.get("region") or (backend and backend.region) or ""
                ).lower()

                def _by_code(code_name):
                    return Currency.search([("name", "=", code_name)], limit=1)

                # UK / GB → GBP
                if "uk" in code or ".co.uk" in name or code == "GB":
                    currency = _by_code("GBP")
                # JP → JPY
                elif code == "JP" or "japan" in name:
                    currency = _by_code("JPY")
                # CA → CAD
                elif code == "CA" or "canada" in name:
                    currency = _by_code("CAD")
                # AU → AUD
                elif code == "AU" or "australia" in name:
                    currency = _by_code("AUD")
                # EU region → EUR (covers most EU marketplaces)
                elif region == "eu" or "europe" in region:
                    currency = _by_code("EUR")
                # NA region → USD
                elif (
                    region == "na" or "north america" in region or code in ("US", "MX")
                ):
                    currency = _by_code("USD")

            # Company currency fallback
            if not currency and self.env.company.currency_id:
                currency = self.env.company.currency_id

            # Last resort: any currency
            if not currency:
                currency = Currency.search([], limit=1)

            if currency:
                vals["currency_id"] = currency.id

        return super().create(vals)

    def get_delivery_carrier_for_amazon_shipping(self, ship_service_level):
        """Map Amazon shipping level to Odoo delivery carrier

        Args:
            ship_service_level: Amazon ShipServiceLevel value

        Returns:
            delivery.carrier record or empty recordset
        """
        self.ensure_one()

        # Mapping from Amazon shipping levels to fields
        mapping = {
            "Standard": "delivery_standard_id",
            "Expedited": "delivery_expedited_id",
            "Priority": "delivery_priority_id",
            "NextDay": "delivery_priority_id",
            "SecondDay": "delivery_expedited_id",
            "Scheduled": "delivery_scheduled_id",
        }

        field_name = mapping.get(ship_service_level, "delivery_default_id")
        carrier = self[field_name]

        # Fallback to default if specific mapping not configured
        if not carrier and field_name != "delivery_default_id":
            carrier = self.delivery_default_id

        return carrier
