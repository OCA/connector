# Copyright 2016 Camptocamp SA
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html)

from odoo import fields, models


class TestComponentCollection(models.Model):

    _name = 'test.component.collection'
    _inherit = ['collection.base']

    name = fields.Char()
