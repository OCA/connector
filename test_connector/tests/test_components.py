# -*- coding: utf-8 -*-
# Copyright 2013-2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo.tests import common
from odoo.addons.connector.components.builder import components


class TestComponentInheritance(common.TransactionCase):

    def setUp(self):
        super(TestComponentInheritance, self).setUp()

    def test_inherit_base(self):
        component = components['base']()
        self.assertEquals('test_inherit_base', component.test_inherit_base())

    def test_inherit_component(self):
        component = components['mapper']()
        self.assertEquals('test_inherit_component',
                          component.test_inherit_component())

    def test_inherit_prototype_component(self):
        component = components['test.mapper']()
        self.assertEquals('test_inherit_component',
                          component.test_inherit_component())
        self.assertEquals('test.mapper', component.name())
