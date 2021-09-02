# Copyright 2017 Camptocamp SA
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html)

from odoo.addons.component.core import AbstractComponent, Component


class BaseComponent(AbstractComponent):
    _inherit = 'base'

    def test_inherit_base(self):
        return 'test_inherit_base'


class Mapper(AbstractComponent):
    _name = 'mapper'

    def test_inherit_component(self):
        return 'test_inherit_component'


class ImportTestMapper(Component):
    _name = 'test.mapper'
    _inherit = 'mapper'
    _usage = 'import.mapper'
    _collection = 'test.component.collection'

    def name(self):
        return 'test.mapper'


class UserTestComponent(Component):
    _name = 'test.user.component'
    _apply_on = ['res.users']
    _usage = 'test1'
    _collection = 'test.component.collection'
