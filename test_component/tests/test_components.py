# -*- coding: utf-8 -*-
# Copyright 2013-2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo.tests import common
from odoo.addons.component.core import all_components


class TestComponentInheritance(common.TransactionCase):

    def setUp(self):
        super(TestComponentInheritance, self).setUp()
        self.collection = self.env['test.component.collection'].create(
            {'name': 'Test'}
        )
        self.work = self.collection.work_on('res.users')


    def test_inherit_base(self):
        component = all_components['base'](self.work)
        self.assertEquals('test_inherit_base', component.test_inherit_base())

    def test_inherit_component(self):
        component = all_components['mapper'](self.work)
        self.assertEquals('test_inherit_component',
                          component.test_inherit_component())

    def test_inherit_prototype_component(self):
        component = all_components['test.mapper'](self.work)
        self.assertEquals('test_inherit_component',
                          component.test_inherit_component())
        self.assertEquals('test.mapper', component.name())
