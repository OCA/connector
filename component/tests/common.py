# -*- coding: utf-8 -*-
# Copyright 2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import unittest2
from odoo.tests import common
from odoo.addons.component.core import (
    AbstractComponent,
    ComponentGlobalRegistry,
    MetaComponent,
)


class ComponentRegistryCase(unittest2.TestCase):

    def setUp(self):
        super(ComponentRegistryCase, self).setUp()
        self._original_components = MetaComponent._modules_components.copy()
        MetaComponent._modules_components.clear()

        self.comp_registry = ComponentGlobalRegistry()

        # there's always an implicit dependency on a 'base' component
        # so we must register one
        class Base(AbstractComponent):
            _name = 'base'

        Base._build_component(self.comp_registry)

    def tearDown(self):
        super(ComponentRegistryCase, self).tearDown()
        MetaComponent._modules_components = self._original_components

    def _build_components(self, *classes):
        for cls in classes:
            cls._build_component(self.comp_registry)


class TransactionComponentRegistryCase(common.TransactionCase,
                                       ComponentRegistryCase):

    def setUp(self):
        common.TransactionCase.setUp(self)
        ComponentRegistryCase.setUp(self)
        self.collection = self.env['collection.base']

    def teardown(self):
        common.TransactionCase.tearDown(self)
        ComponentRegistryCase.tearDown(self)
