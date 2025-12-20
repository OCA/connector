from odoo import fields, models


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
