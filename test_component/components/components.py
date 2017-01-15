# -*- coding: utf-8 -*-
# Copyright 2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo.addons.component.core import Component


class BaseComponent(Component):
    _inherit = 'base'

    def test_inherit_base(self):
        return 'test_inherit_base'


class Mapper(Component):
    _name = 'mapper'

    def test_inherit_component(self):
        return 'test_inherit_component'


class TestMapper(Component):
    _name = 'test.mapper'
    _inherit = 'mapper'

    def name(self):
        return 'test.mapper'


class TestUserComponent(Component):
    _name = 'test.user.component'
    _apply_on = ['res.users']
