# Copyright 2017 Camptocamp SA
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html)

import copy

from contextlib import contextmanager

import unittest
import odoo
from odoo import api
from odoo.tests import common
from odoo.addons.component.core import (
    ComponentRegistry,
    MetaComponent,
    _get_addon_name,
)


@contextmanager
def new_rollbacked_env():
    registry = odoo.registry(common.get_db_name())
    uid = odoo.SUPERUSER_ID
    cr = registry.cursor()
    try:
        yield api.Environment(cr, uid, {})
    finally:
        cr.rollback()  # we shouldn't have to commit anything
        cr.close()


class ComponentMixin(object):

    @classmethod
    def setUpComponent(cls):
        with new_rollbacked_env() as env:
            builder = env['component.builder']
            # build the components of every installed addons
            comp_registry = builder._init_global_registry()
            cls._components_registry = comp_registry
            # ensure that we load only the components of the 'installed'
            # modules, not 'to install', which means we load only the
            # dependencies of the tested addons, not the siblings or
            # chilren addons
            builder.build_registry(comp_registry, states=('installed',))
            # build the components of the current tested addon
            current_addon = _get_addon_name(cls.__module__)
            env["component.builder"].load_components(current_addon)

    def setUp(self):
        # should be ready only during tests, never during installation
        # of addons
        self._components_registry.ready = True

        @self.addCleanup
        def notready():
            self._components_registry.ready = False


class TransactionComponentCase(common.TransactionCase, ComponentMixin):
    """ A TransactionCase that loads all the components

    It it used like an usual Odoo's TransactionCase, but it ensures
    that all the components of the current addon and its dependencies
    are loaded.

    """

    @classmethod
    def setUpClass(cls):
        super(TransactionComponentCase, cls).setUpClass()
        super().setUpClass()
        cls.setUpComponent()

    def setUp(self):
        # resolve an inheritance issue (common.TransactionCase does not call
        # super)
        common.TransactionCase.setUp(self)
        ComponentMixin.setUp(self)
        # There's no env on setUpClass of TransactionCase, must do it here.
        self.env.context = dict(
            self.env.context, components_registry=self._components_registry
        )


class SavepointComponentCase(common.SavepointCase, ComponentMixin):
    """ A SavepointCase that loads all the components

    It it used like an usual Odoo's SavepointCase, but it ensures
    that all the components of the current addon and its dependencies
    are loaded.

    """

    @classmethod
    def setUpClass(cls):
        super(SavepointComponentCase, cls).setUpClass()
        cls.setUpComponent()

    def setUp(self):
        # resolve an inheritance issue (common.SavepointCase does not call
        # super)
        common.SavepointCase.setUp(self)
        ComponentMixin.setUp(self)


class ComponentRegistryCase(unittest.TestCase):
    """ This test case can be used as a base for writings tests on components

    This test case is meant to test components in a special component registry,
    where you want to have maximum control on which components are loaded
    or not, or when you want to create additional components in your tests.

    If you only want to *use* the components of the tested addon in your tests,
    then consider using one of:

    * :class:`TransactionComponentCase`
    * :class:`SavepointComponentCase`

    This test case creates a special
    :class:`odoo.addons.component.core.ComponentRegistry` for the purpose of
    the tests. By default, it loads all the components of the dependencies, but
    not the components of the current addon (which you have to handle
    manually). In your tests, you can add more components in 2 manners.

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

    @staticmethod
    def _setup_registry(class_or_instance):
        # keep the original classes registered by the metaclass
        # so we'll restore them at the end of the tests, it avoid
        # to pollute it with Stub / Test components
        class_or_instance._original_components = copy.deepcopy(
            MetaComponent._modules_components
        )

        # it will be our temporary component registry for our test session
        class_or_instance.comp_registry = ComponentRegistry()

        # it builds the 'final component' for every component of the
        # 'component' addon and push them in the component registry
        class_or_instance.comp_registry.load_components("component")
        # build the components of every installed addons already installed
        # but the current addon (when running with pytest/nosetest, we
        # simulate the --test-enable behavior by excluding the current addon
        # which is in 'to install' / 'to upgrade' with --test-enable).
        current_addon = _get_addon_name(class_or_instance.__module__)
        with new_rollbacked_env() as env:
            env["component.builder"].build_registry(
                class_or_instance.comp_registry,
                states=("installed",),
                exclude_addons=[current_addon],
            )

        # Fake that we are ready to work with the registry
        # normally, it is set to True and the end of the build
        # of the components. Here, we'll add components later in
        # the components registry, but we don't mind for the tests.
        class_or_instance.comp_registry.ready = True
        if hasattr(class_or_instance, "env"):
            # let it propagate via ctx
            class_or_instance.env.context = dict(
                class_or_instance.env.context,
                components_registry=class_or_instance.comp_registry,
            )

    @staticmethod
    def _teardown_registry(class_or_instance):
        # restore the original metaclass' classes
        MetaComponent._modules_components = class_or_instance._original_components

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
        ComponentRegistryCase._setup_registry(self)
        self.collection = self.env["collection.base"]

    def tearDown(self):
        ComponentRegistryCase._teardown_registry(self)
        ComponentRegistryCase.tearDown(self)
        common.TransactionCase.tearDown(self)


class SavepointComponentRegistryCase(common.SavepointCase,
                                     ComponentRegistryCase):
    """ Adds Odoo Transaction with Savepoint in the base Component TestCase """

    def setUp(self):
        # resolve an inheritance issue (common.SavepointCase does not use
        # super)
        common.SavepointCase.setUp(self)
        ComponentRegistryCase.setUp(self)
        ComponentRegistryCase._setup_registry(self)
        self.collection = self.env['collection.base']

    def tearDown(self):
        ComponentRegistryCase.tearDown(self)
        common.SavepointCase.tearDown(self)
