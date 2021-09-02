# Copyright 2013-2017 Camptocamp SA
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html)

from odoo.addons.component.tests.common import TransactionComponentCase
from odoo.addons.test_component.components.components import UserTestComponent


class TestComponentCollection(TransactionComponentCase):

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
            self.assertEqual(UserTestComponent._name, component._name)

    def test_components_usage(self):
        with self.collection.work_on('res.users') as work:
            component = work.component(usage='test1')
            self.assertEqual(UserTestComponent._name, component._name)
