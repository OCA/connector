# Copyright 2017 Camptocamp SA
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html)

{
    "name": "Connector Tests",
    "summary": "Automated tests for Connector, do not install.",
    "version": "16.0.1.0.0",
    "author": "Camptocamp,Odoo Community Association (OCA)",
    "license": "LGPL-3",
    "category": "Hidden",
    "depends": ["connector"],
    "website": "https://github.com/OCA/connector",
    "data": [
        "security/ir.model.access.csv",
        "data/queue_job_function_data.xml",
    ],
    "installable": True,
}
