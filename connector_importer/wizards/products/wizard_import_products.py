# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2017 Camptocamp (<http://www.camptocamp.com>)
#
##############################################################################

from odoo import fields
from odoo import models

from odoo.addons.connector_importer.models.recordset import AVAILABLE_IMPORTS

AREA = 'products'
PREFIX = 'products_'
# XXX: should we dafine this mapping in backend models instead?
AVAILABLE = [x[0] for x in AVAILABLE_IMPORTS
             if x[0].startswith(PREFIX)]


class WizardImportProducts(models.TransientModel):

    _name = 'wiz.connector.import.products'
    _inherit = 'wiz.connector.import.base'
    _description = "Import product templates and variants"

    AREA = AREA
    PREFIX = PREFIX
    AVAILABLE = AVAILABLE

    default = fields.Binary('products.csv')
    default_filename = fields.Char('Filename')
