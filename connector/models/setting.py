# Copyright 2013-2017 Camptocamp SA
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html)

from odoo import models


class ConnectorConfigSettings(models.TransientModel):

    _name = 'connector.config.settings'
    _description = 'Connector Configuration'
    _inherit = 'res.config.settings'
