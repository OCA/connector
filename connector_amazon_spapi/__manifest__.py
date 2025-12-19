# Copyright 2026 Kencove
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html)

{
    "name": "Amazon SP-API Connector",
    "version": "16.0.1.0.0",
    "category": "Connector",
    "summary": (
        "Amazon Seller Central (SP-API) integration for orders, " "stock, and prices"
    ),
    "author": "Kencove, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/connector",
    "license": "LGPL-3",
    "depends": [
        "connector",
        "sale_management",
        "stock",
        "product",
        "queue_job",
        "delivery",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/ir_cron.xml",
        "views/backend_view.xml",
        "views/marketplace_view.xml",
        "views/shop_view.xml",
        "views/product_binding_view.xml",
        "views/competitive_price_view.xml",
        "views/order_view.xml",
        "views/feed_view.xml",
        "views/amazon_menu.xml",
    ],
    "external_dependencies": {
        "python": [
            "requests",
        ],
    },
    "installable": True,
    "application": False,
}
