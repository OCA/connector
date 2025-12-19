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

    # TODO: map Pricing API response into pricelist items
