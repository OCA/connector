# -*- coding: utf-8 -*-
# Copyright 2016 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo.addons.connector.connector import Binder
from ..backend import test_backend


@test_backend
class ConnectorTestBinder(Binder):

    _model_name = [
        'connector.test.binding',
    ]


@test_backend
class NoInheritsBinder(Binder):

    _model_name = [
        'no.inherits.binding',
    ]

    def unwrap_binding(self, binding):
        raise ValueError('Not an inherits')

    def unwrap_model(self):
        raise ValueError('Not an inherits')
