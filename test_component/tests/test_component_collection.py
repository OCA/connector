# -*- coding: utf-8 -*-
# Copyright 2013-2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo.tests import common
from odoo.addons.test_component.components.components import UserTestComponent


class TestComponentCollection(common.TransactionCase):

    at_install = False
    post_install = True

    def setUp(self):
        super(TestComponentCollection, self).setUp()
        self.collection = self.env['test.component.collection'].create(
            {'name': 'Test'}
        )

    def tearDown(self):
        super(TestComponentCollection, self).tearDown()

    def test_component_by_name(self):
        with self.collection.work_on('res.users') as work:
            component = work.component_by_name(name='test.user.component')
            self.assertEquals(UserTestComponent._name, component._name)

    def test_components_usage(self):
        with self.collection.work_on('res.users') as work:
            component = work.component(usage='test1')
            self.assertEquals(UserTestComponent._name, component._name)
