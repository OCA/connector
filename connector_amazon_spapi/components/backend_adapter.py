from odoo.addons.component.core import Component


class AmazonBaseAdapter(Component):
    _name = "amazon.adapter"
    _inherit = "base.backend.adapter"
    _usage = "backend.adapter"
    _backend_model_name = "amazon.backend"

    def _auth(self):
        # TODO: inject SP-API client with LWA + STS + throttling
        raise NotImplementedError


class AmazonOrdersAdapter(AmazonBaseAdapter):
    _name = "amazon.orders.adapter"
    _usage = "orders.adapter"

    def list_orders(
        self, backend_record, marketplace, updated_after=None, created_after=None
    ):
        # TODO: implement getOrders/getOrderItems with cursors
        raise NotImplementedError


class AmazonPricingAdapter(AmazonBaseAdapter):
    _name = "amazon.pricing.adapter"
    _usage = "pricing.adapter"

    def get_prices(self, backend_record, marketplace, skus):
        # TODO: call Pricing API, return pricing payloads
        raise NotImplementedError

    def push_prices(self, backend_record, marketplace, payload):
        # TODO: send price feed
        raise NotImplementedError


class AmazonInventoryAdapter(AmazonBaseAdapter):
    _name = "amazon.inventory.adapter"
    _usage = "inventory.adapter"

    def push_inventory(self, backend_record, marketplace, payload):
        # TODO: send stock feed
        raise NotImplementedError
