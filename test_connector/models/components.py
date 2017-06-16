# -*- coding: utf-8 -*-
# Copyright 2016 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo.addons.component.core import Component


class ConnectorTestBinder(Component):
    _name = 'connector.test.binder'
    _inherit = ['base.binder']
    _apply_on = [
        'connector.test.binding',
    ]


class NoInheritsBinder(Component):
    _name = 'connector.test.no.inherits.binder'
    _inherit = ['base.binder']
    _apply_on = [
        'no.inherits.binding',
    ]

    def unwrap_binding(self, binding):
        raise ValueError('Not an inherits')

    def unwrap_model(self):
        raise ValueError('Not an inherits')
