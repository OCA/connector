# -*- coding: utf-8 -*-
# Copyright 2013-2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo.tests import common
from odoo.addons.connector.components.collection import (
    collection_registry,
    use,
)
from odoo.addons.test_connector.components.components import TestMapper


class TestComponentCollection(common.TransactionCase):

    def setUp(self):
        super(TestComponentCollection, self).setUp()
        self._previous_backends = collection_registry._backends
        collection_registry._backends = {}

    def tearDown(self):
        super(TestComponentCollection, self).tearDown()
        collection_registry._backends = self._previous_backends

    def test_register_component(self):
        collection_registry.register('test.backend', TestMapper)
        component = collection_registry.find('test.backend',
                                             name='test.mapper')
        self.assertEquals(TestMapper, component)

    def test_register_component_with_use(self):
        use(TestMapper, 'test.backend')
        component = collection_registry.find('test.backend',
                                             name='test.mapper')
        self.assertEquals(TestMapper, component)
