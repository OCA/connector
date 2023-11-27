# -*- coding: utf-8 -*-
# Copyright 2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo.addons.component.tests.common import TransactionComponentCase


class TestComponentInheritance(TransactionComponentCase):

    def setUp(self):
        super(TestComponentInheritance, self).setUp()
        self.collection = self.env['test.component.collection'].create(
            {'name': 'Test'}
        )

    def test_inherit_base(self):
        with self.collection.work_on('res.users') as work:
            component = work.component_by_name('base')
            self.assertEquals('test_inherit_base',
                              component.test_inherit_base())

    def test_inherit_component(self):
        with self.collection.work_on('res.users') as work:
            component = work.component_by_name('mapper')
            self.assertEquals('test_inherit_component',
                              component.test_inherit_component())

    def test_inherit_prototype_component(self):
        with self.collection.work_on('res.users') as work:
            component = work.component_by_name('test.mapper')
            self.assertEquals('test_inherit_component',
                              component.test_inherit_component())
            self.assertEquals('test.mapper', component.name())
