# -*- coding: utf-8 -*-
# Copyright 2016-2017 Cédric Pigeon
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResUsers(models.Model):
    _inherit = 'res.users'

    subscribe_job = fields.Boolean(string='Jobs Notifications',
                                   default=True,
                                   help='If this flag is checked and the'
                                        ' user is Connector Manager, he will'
                                        ' receive job notifications.',
                                   select=True)
