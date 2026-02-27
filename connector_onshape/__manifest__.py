# Copyright 2024 Kencove Farm Fence Supplies
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "Onshape Connector",
    "version": "16.0.1.0.0",
    "category": "Connector",
    "summary": "Synchronize products and BOMs with Onshape PLM",
    "author": "Kencove Farm Fence Supplies, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/connector",
    "license": "AGPL-3",
    "development_status": "Beta",
    "depends": [
        "connector",
        "component",
        "component_event",
        "queue_job",
        "product",
        "mrp",
    ],
    "external_dependencies": {
        "python": ["requests"],
    },
    "data": [
        "security/onshape_security.xml",
        "security/ir.model.access.csv",
        "data/queue_job_channel_data.xml",
        "data/queue_job_function_data.xml",
        "data/ir_cron_data.xml",
        "wizards/onshape_import_wizard_views.xml",
        "views/onshape_backend_views.xml",
        "views/onshape_document_views.xml",
        "views/onshape_product_views.xml",
        "views/product_template_views.xml",
        "views/mrp_bom_views.xml",
    ],
    "installable": True,
    "application": False,
}
