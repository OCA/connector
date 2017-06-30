# -*- coding: utf-8 -*-
# Copyright 2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import copy

import unittest2
from odoo.tests import common
from odoo.addons.component.core import (
    ComponentRegistry,
    MetaComponent,
)


class ComponentRegistryCase(unittest2.TestCase):
    """ This test case can be used as a base for writings tests on components

    It creates a special
    :class:`odoo.addons.componenent.core.ComponentRegistry` for the purpose
    of the tests. It loads the ``base`` component in it. In your tests,
    you can add more components in 2 manners.

    All the components of an Odoo module::

        self._load_module_components('connector')

    Only specific components::

        self._build_components(MyComponent1, MyComponent2)

    Note: for the lookups of the components, the default component
    registry is a global registry for the database. Here, you will
    need to explicitly pass ``self.comp_registry`` in the
    :class:`~odoo.addons.component.core.WorkContext`::

        work = WorkContext(model_name='res.users',
                           collection='my.collection',
                           components_registry=self.comp_registry)

    Or::

        collection_record = self.env['my.collection'].browse(1)
        with collection_record.work_on(
                'res.partner',
                components_registry=self.comp_registry) as work:

    """

    def setUp(self):
        super(ComponentRegistryCase, self).setUp()

        # keep the original classes registered by the metaclass
        # so we'll restore them at the end of the tests, it avoid
        # to pollute it with Stub / Test components
        self._original_components = copy.deepcopy(
            MetaComponent._modules_components
        )

        # it will be our temporary component registry for our test session
        self.comp_registry = ComponentRegistry()

        # it builds the 'final component' for every component of the
        # 'component' addon and push them in the component registry
        self.comp_registry.load_components('component')

        # Fake that we are ready to work with the registry
        # normally, it is set to True and the end of the build
        # of the components. Here, we'll add components later in
        # the components registry, but we don't mind for the tests.
        self.comp_registry.ready = True

    def tearDown(self):
        super(ComponentRegistryCase, self).tearDown()
        # restore the original metaclass' classes
        MetaComponent._modules_components = self._original_components

    def _load_module_components(self, module):
        self.comp_registry.load_components(module)

    def _build_components(self, *classes):
        for cls in classes:
            cls._build_component(self.comp_registry)


class TransactionComponentRegistryCase(common.TransactionCase,
                                       ComponentRegistryCase):
    """ Adds Odoo Transaction in the base Component TestCase """

    def setUp(self):
        # resolve an inheritance issue (common.TransactionCase does not use
        # super)
        common.TransactionCase.setUp(self)
        ComponentRegistryCase.setUp(self)
        self.collection = self.env['collection.base']

        # build the components of every installed addons
        self.env['component.builder'].build_registry(self.comp_registry)

    def teardown(self):
        common.TransactionCase.tearDown(self)
        ComponentRegistryCase.tearDown(self)
