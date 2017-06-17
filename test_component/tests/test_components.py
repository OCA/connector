# -*- coding: utf-8 -*-
# Copyright 2013-2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo.tests import common
from odoo.addons.component.core import _component_databases


class TestComponentInheritance(common.TransactionCase):

    at_install = False
    post_install = True

    def setUp(self):
        super(TestComponentInheritance, self).setUp()
        self.collection = self.env['test.component.collection'].create(
            {'name': 'Test'}
        )
        self.work = self.collection.work_on('res.users')
        dbname = self.env.cr.dbname
        self.components_registry = _component_databases[dbname]

    def test_inherit_base(self):
        component = self.components_registry['base'](self.work)
        self.assertEquals('test_inherit_base', component.test_inherit_base())

    def test_inherit_component(self):
        component = self.components_registry['mapper'](self.work)
        self.assertEquals('test_inherit_component',
                          component.test_inherit_component())

    def test_inherit_prototype_component(self):
        component = self.components_registry['test.mapper'](self.work)
        self.assertEquals('test_inherit_component',
                          component.test_inherit_component())
        self.assertEquals('test.mapper', component.name())
