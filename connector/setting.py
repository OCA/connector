# -*- coding: utf-8 -*-
# Copyright 2013-2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import models


class ConnectorConfigSettings(models.TransientModel):

    _name = 'connector.config.settings'
    _description = 'Connector Configuration'
    _inherit = 'base.config.settings'
