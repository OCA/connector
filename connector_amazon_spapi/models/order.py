from odoo import api, fields, models


class AmazonSaleOrder(models.Model):
    _name = "amazon.sale.order"
    _description = "Amazon Sale Order"
    _inherit = "external.binding"
    _inherits = {"sale.order": "odoo_id"}

    odoo_id = fields.Many2one(
        comodel_name="sale.order",
        string="Odoo Sale Order",
        required=True,
        ondelete="cascade",
    )
    backend_id = fields.Many2one(
        comodel_name="amazon.backend",
        required=True,
        ondelete="restrict",
    )
    shop_id = fields.Many2one(comodel_name="amazon.shop", ondelete="set null")
    marketplace_id = fields.Many2one(
        comodel_name="amazon.marketplace", ondelete="set null"
    )
    external_id = fields.Char(string="Amazon Order ID", required=True)
    purchase_date = fields.Datetime()
    last_update_date = fields.Datetime()
    fulfillment_channel = fields.Selection(
        selection=[("AFN", "Fulfilled by Amazon"), ("MFN", "Fulfilled by Merchant")]
    )
    status = fields.Char(string="Amazon Order Status")
    last_sync = fields.Datetime()
    shipment_confirmed = fields.Boolean(default=False)
    last_shipment_push = fields.Datetime()

    _sql_constraints = [
        (
            "amazon_order_unique",
            "unique(backend_id, external_id)",
            "An Amazon order with this ID already exists for the backend.",
        ),
    ]

    @api.model
    def _create_or_update_from_amazon(self, shop, amazon_order):
        """Create or update Odoo order from Amazon order data"""
        amazon_order_id = amazon_order.get("AmazonOrderId")

        # Find existing binding
        binding = self.search(
            [
                ("backend_id", "=", shop.backend_id.id),
                ("external_id", "=", amazon_order_id),
            ],
            limit=1,
        )

        # Get delivery carrier from Amazon shipping level
        ship_service_level = amazon_order.get("ShipServiceLevel")
        carrier = shop.marketplace_id.get_delivery_carrier_for_amazon_shipping(
            ship_service_level
        )

        # Prepare base order values
        order_vals_base = {
            "partner_id": self._get_or_create_partner(amazon_order).id,
            "company_id": shop.company_id.id,
            "warehouse_id": shop.warehouse_id.id if shop.warehouse_id else False,
            "pricelist_id": shop.pricelist_id.id if shop.pricelist_id else False,
            "carrier_id": carrier.id if carrier else False,
            "date_order": amazon_order.get("PurchaseDate"),
        }

        binding_vals = {
            "backend_id": shop.backend_id.id,
            "shop_id": shop.id,
            "marketplace_id": shop.marketplace_id.id,
            "external_id": amazon_order_id,
            "purchase_date": amazon_order.get("PurchaseDate"),
            "last_update_date": amazon_order.get("LastUpdateDate"),
            "fulfillment_channel": amazon_order.get("FulfillmentChannel"),
            "status": amazon_order.get("OrderStatus"),
        }

        if binding:
            # Update existing order (do not override salesperson/team if set)
            binding.odoo_id.write(order_vals_base)
            binding.write(binding_vals)
        else:
            # Create new order, applying defaults for salesperson and team
            order_vals_create = dict(order_vals_base)
            if shop.default_salesperson_id:
                order_vals_create["user_id"] = shop.default_salesperson_id.id
            if shop.default_sales_team_id:
                order_vals_create["team_id"] = shop.default_sales_team_id.id

            new_order = self.env["sale.order"].create(order_vals_create)
            binding_vals["odoo_id"] = new_order.id
            binding = self.create(binding_vals)

            # Optionally add extra routing line on import
            if shop.add_exp_line and shop.exp_line_product_id:
                self.env["sale.order.line"].create(
                    {
                        "order_id": new_order.id,
                        "product_id": shop.exp_line_product_id.id,
                        "name": shop.exp_line_name or "/EXP-AMZ",
                        "product_uom_qty": shop.exp_line_qty or 1.0,
                        "price_unit": shop.exp_line_price or 0.0,
                    }
                )

        # Sync order lines
        self._sync_order_lines(binding, shop, amazon_order_id)

        return binding

    def _get_last_done_picking(self):
        """Return the most recent done picking for the bound sale orders."""
        self.ensure_one()
        pickings = self.odoo_id.picking_ids.filtered(lambda p: p.state == "done")
        return pickings and pickings[-1] or False

    def _build_shipment_feed_xml(self, picking):
        """Build XML for Order Fulfillment feed for a single order.

        Ref: https://sellercentral.amazon.com/gp/help/200202590
        """
        self.ensure_one()
        if not picking:
            return ""

        carrier_name = picking.carrier_id and picking.carrier_id.name or ""
        tracking = picking.carrier_tracking_ref or ""
        ship_method = (
            self.marketplace_id
            and self.marketplace_id.get_delivery_carrier_for_amazon_shipping(
                self.odoo_id.carrier_id.name
            )
            and self.odoo_id.carrier_id.name
            or "Standard"
        )

        lines_xml = []
        for line in self.odoo_id.order_line:
            # Try to find Amazon line binding to get AmazonOrderItemCode
            line_binding = self.env["amazon.sale.order.line"].search(
                [
                    ("odoo_id", "=", line.id),
                    ("amazon_order_id", "=", self.id),
                ],
                limit=1,
            )
            amazon_item_code = line_binding.external_id or ""
            qty = int(line.product_uom_qty)
            lines_xml.extend(
                [
                    "      <Item>",
                    f"        <AmazonOrderItemCode>{amazon_item_code}</AmazonOrderItemCode>",
                    f"        <Quantity>{qty}</Quantity>",
                    "      </Item>",
                ]
            )

        xml_lines = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<AmazonEnvelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"',
            '    xsi:noNamespaceSchemaLocation="amzn-envelope.xsd">',
            "  <Header>",
            "    <DocumentVersion>1.01</DocumentVersion>",
            f"    <MerchantIdentifier>{self.backend_id.lwa_client_id}</MerchantIdentifier>",
            "  </Header>",
            "  <MessageType>OrderFulfillment</MessageType>",
            "  <Message>",
            "    <MessageID>1</MessageID>",
            "    <OrderFulfillment>",
            f"      <AmazonOrderID>{self.external_id}</AmazonOrderID>",
            "      <FulfillmentDate>"
            + (
                fields.Datetime.to_string(picking.date_done)
                if picking.date_done
                else fields.Datetime.now()
            )
            + "</FulfillmentDate>",
            "      <FulfillmentData>",
            f"        <CarrierName>{carrier_name}</CarrierName>",
            f"        <ShippingMethod>{ship_method}</ShippingMethod>",
            f"        <ShipperTrackingNumber>{tracking}</ShipperTrackingNumber>",
            "      </FulfillmentData>",
            *lines_xml,
            "    </OrderFulfillment>",
            "  </Message>",
            "</AmazonEnvelope>",
        ]

        return "\n".join(xml_lines)

    def push_shipment(self):
        """Create and submit a fulfillment feed for this order's latest shipment."""
        self.ensure_one()
        picking = self._get_last_done_picking()
        if not picking:
            return False

        feed_xml = self._build_shipment_feed_xml(picking)
        if not feed_xml:
            return False

        feed = self.env["amazon.feed"].create(
            {
                "backend_id": self.backend_id.id,
                "marketplace_id": self.marketplace_id.id,
                "feed_type": "POST_ORDER_FULFILLMENT_DATA",
                "state": "draft",
                "payload_json": feed_xml,
            }
        )

        feed.with_delay().submit_feed()
        self.write(
            {
                "shipment_confirmed": True,
                "last_shipment_push": fields.Datetime.now(),
            }
        )
        return True

    def _get_or_create_partner(self, amazon_order):
        """Get or create partner from Amazon order data

        Attempts to find existing partner by email, then by name+address.
        Creates new partner if no match found.
        """
        shipping_address = amazon_order.get("ShippingAddress", {})
        buyer_info = amazon_order.get("BuyerInfo", {})

        email = buyer_info.get("BuyerEmail", "").strip()
        name = shipping_address.get("Name", "Amazon Customer")

        # Try to find by email first
        if email:
            partner = self.env["res.partner"].search([("email", "=", email)], limit=1)
            if partner:
                return partner

        # Try to find by name and address
        street = shipping_address.get("AddressLine1", "")
        city = shipping_address.get("City", "")
        zip_code = shipping_address.get("PostalCode", "")

        if name and street and city:
            partner = self.env["res.partner"].search(
                [
                    ("name", "=", name),
                    ("street", "=", street),
                    ("city", "=", city),
                ],
                limit=1,
            )
            if partner:
                return partner

        # Create new partner
        country = self._get_country_from_code(shipping_address.get("CountryCode"))
        state = self._get_state_from_code(
            shipping_address.get("StateOrRegion"), country
        )

        partner_vals = {
            "name": name,
            "email": email or False,
            "phone": shipping_address.get("Phone", False),
            "street": street,
            "street2": shipping_address.get("AddressLine2", False),
            "city": city,
            "zip": zip_code,
            "country_id": country.id if country else False,
            "state_id": state.id if state else False,
            "customer_rank": 1,
            "comment": f"Created from Amazon order {amazon_order.get('AmazonOrderId')}",
        }

        return self.env["res.partner"].create(partner_vals)

    def _get_country_from_code(self, country_code):
        """Get country record from ISO code"""
        if not country_code:
            return self.env["res.country"]
        return self.env["res.country"].search(
            [("code", "=", country_code.upper())], limit=1
        )

    def _get_state_from_code(self, state_code, country):
        """Get state record from code and country"""
        if not state_code or not country:
            return self.env["res.country.state"]
        return self.env["res.country.state"].search(
            [
                ("code", "=", state_code.upper()),
                ("country_id", "=", country.id),
            ],
            limit=1,
        )

    def _sync_order_lines(self, binding, shop, amazon_order_id):
        """Sync order lines from Amazon"""
        # Call SP-API to get order items
        result = shop.backend_id._call_sp_api(
            "GET",
            f"/orders/v0/orders/{amazon_order_id}/orderItems",
        )

        order_items = result.get("payload", {}).get("OrderItems", [])
        line_model = self.env["amazon.sale.order.line"]

        for item in order_items:
            line_model._create_or_update_from_amazon(binding, shop, item)


class AmazonSaleOrderLine(models.Model):
    _name = "amazon.sale.order.line"
    _description = "Amazon Sale Order Line"
    _inherit = "external.binding"
    _inherits = {"sale.order.line": "odoo_id"}

    odoo_id = fields.Many2one(
        comodel_name="sale.order.line",
        required=True,
        ondelete="cascade",
    )
    backend_id = fields.Many2one(
        comodel_name="amazon.backend",
        required=True,
        ondelete="restrict",
    )
    amazon_order_id = fields.Many2one(
        comodel_name="amazon.sale.order",
        required=True,
        ondelete="cascade",
    )
    product_binding_id = fields.Many2one(
        comodel_name="amazon.product.binding",
        ondelete="set null",
    )
    external_id = fields.Char(string="Amazon Order Line ID")
    seller_sku = fields.Char(string="Seller SKU")

    @api.model
    def _create_or_update_from_amazon(self, amazon_order_binding, shop, amazon_item):
        """Create or update order line from Amazon item data"""
        item_id = amazon_item.get("OrderItemId")
        seller_sku = amazon_item.get("SellerSKU")

        # Find existing line binding
        binding = self.search(
            [
                ("amazon_order_id", "=", amazon_order_binding.id),
                ("external_id", "=", item_id),
            ],
            limit=1,
        )

        # Find product by SKU
        product = self._get_product_by_sku(shop, seller_sku)

        # Prepare line values
        quantity = float(amazon_item.get("QuantityOrdered", 0))
        unit_price = float(amazon_item.get("ItemPrice", {}).get("Amount", 0))

        line_vals = {
            "order_id": amazon_order_binding.odoo_id.id,
            "product_id": product.id if product else False,
            "product_uom_qty": quantity,
            "price_unit": unit_price,
            "name": amazon_item.get("Title", "Amazon Product"),
        }

        binding_vals = {
            "backend_id": shop.backend_id.id,
            "amazon_order_id": amazon_order_binding.id,
            "external_id": item_id,
            "seller_sku": seller_sku,
        }

        if binding:
            # Update existing line
            binding.odoo_id.write(line_vals)
            binding.write(binding_vals)
        else:
            # Create new line
            binding_vals["odoo_id"] = self.env["sale.order.line"].create(line_vals).id
            binding = self.create(binding_vals)

        return binding

    def _get_product_by_sku(self, shop, seller_sku):
        """Find product by Amazon SKU"""
        # TODO: Implement product matching logic via amazon.product.binding
        # For now, search by default_code (internal reference)
        return self.env["product.product"].search(
            [("default_code", "=", seller_sku)], limit=1
        )
