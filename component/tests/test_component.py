# -*- coding: utf-8 -*-
# Copyright 2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo.addons.component.core import (
    Component,
)
from .common import TransactionComponentRegistryCase
from odoo.addons.component.exception import (
    NoComponentError,
    SeveralComponentError,
)


class TestComponent(TransactionComponentRegistryCase):
    """ Test usage of components

    These tests are a bit more broad that mere unit tests.
    We test the chain odoo Model -> generate a WorkContext instance -> Work
    with Component.

    Tests are inside Odoo transactions, so we can work
    with Odoo's env / models.
    """

    def setUp(self):
        super(TestComponent, self).setUp()
        self.collection = self.env['collection.base']

        # create some Component to play with
        class Component1(Component):
            _name = 'component1'
            _collection = 'collection.base'
            _usage = 'for.test'
            _apply_on = ['res.partner']

        class Component2(Component):
            _name = 'component2'
            _collection = 'collection.base'
            _usage = 'for.test'
            _apply_on = ['res.users']

        # build the components and register them in our
        # test component registry
        Component1._build_component(self.comp_registry)
        Component2._build_component(self.comp_registry)

        # our collection, in a less abstract use case, it
        # could be a record of 'magento.backend' for instance
        self.collection_record = self.collection.new()
        # Our WorkContext, it will be passed along in every
        # components so we can share data transversally.
        # We are working with res.partner in the following tests,
        # unless we change it in the test.
        self.work = self.collection_record.work_on(
            'res.partner',
            # we use a custom registry only
            # for the sake of the tests
            components_registry=self.comp_registry
        )
        # We get the 'base' component, handy to test the base
        # methods component, many_components, ...
        self.base = self.work.component_by_name('base')

    def test_component_attrs(self):
        """ Basic access to a Component's attribute """
        # as we are working on res.partner, we should get 'component1'
        comp = self.work.component(usage='for.test')
        # but this is not what we test here, we test the attributes:
        self.assertEquals(self.collection_record, comp.collection)
        self.assertEquals(self.work, comp.work)
        self.assertEquals(self.env, comp.env)
        self.assertEquals(self.env['res.partner'], comp.model)

    def test_component_get_by_name_same_model(self):
        """ Use component_by_name with current working model """
        # we ask a component directly by it's name, considering
        # we work with res.partner, we should get 'component1'
        # this is ok because it's _apply_on contains res.partner
        comp = self.base.component_by_name('component1')
        self.assertEquals('component1', comp._name)
        self.assertEquals(self.env['res.partner'], comp.model)

    def test_component_get_by_name_other_model(self):
        """ Use component_by_name with another model """
        # we ask a component directly by it's name, but we
        # want to work with 'res.users', this is ok since
        # component2's _apply_on contains res.users
        comp = self.base.component_by_name(
            'component2', model_name='res.users'
        )
        self.assertEquals('component2', comp._name)
        self.assertEquals(self.env['res.users'], comp.model)
        # what happens under the hood, is that a new WorkContext
        # has been created for this model, with all the other values
        # identical to the previous WorkContext (the one for res.partner)
        # We can check that with:
        self.assertNotEquals(self.work, comp.work)
        self.assertEquals('res.partner', self.work.model_name)
        self.assertEquals('res.users', comp.work.model_name)

    def test_component_get_by_name_wrong_model(self):
        """ Use component_by_name with a model not in _apply_on """
        msg = ("Component with name 'component2' can't be used "
               "for model 'res.partner'.*")
        with self.assertRaisesRegexp(NoComponentError, msg):
            # we ask for the model 'component2' but we are working
            # with res.partner, and it only accepts res.users
            self.base.component_by_name('component2')

    def test_component_get_by_name_not_exist(self):
        """ Use component_by_name on a component that do not exist """
        msg = "No component with name 'foo' found."
        with self.assertRaisesRegexp(NoComponentError, msg):
            self.base.component_by_name('foo')

    def test_component_by_usage_same_model(self):
        """ Use component(usage=...) on the same model """
        # we ask for a component having _usage == 'for.test', and
        # model being res.partner (the model in the current WorkContext)
        comp = self.base.component(usage='for.test')
        self.assertEquals('component1', comp._name)
        self.assertEquals(self.env['res.partner'], comp.model)

    def test_component_by_usage_other_model(self):
        """ Use component(usage=...) on a different model (name) """
        # we ask for a component having _usage == 'for.test', and
        # a different model (res.users)
        comp = self.base.component(usage='for.test', model_name='res.users')
        self.assertEquals('component2', comp._name)
        self.assertEquals(self.env['res.users'], comp.model)
        # what happens under the hood, is that a new WorkContext
        # has been created for this model, with all the other values
        # identical to the previous WorkContext (the one for res.partner)
        # We can check that with:
        self.assertNotEquals(self.work, comp.work)
        self.assertEquals('res.partner', self.work.model_name)
        self.assertEquals('res.users', comp.work.model_name)

    def test_component_by_usage_other_model_env(self):
        """ Use component(usage=...) on a different model (instance) """
        comp = self.base.component(usage='for.test',
                                   model_name=self.env['res.users'])
        self.assertEquals('component2', comp._name)
        self.assertEquals(self.env['res.users'], comp.model)

    def test_component_error_several(self):
        """ Use component(usage=...) when more than one component match """
        # we create a new Component with _usage 'for.test', in the same
        # collection and no _apply_on
        class Component3(Component):
            _name = 'component3'
            _collection = 'collection.base'
            _usage = 'for.test'

        Component3._build_component(self.comp_registry)

        with self.assertRaises(SeveralComponentError):
            # When a component has no _apply_on, it means it can be applied
            # on *any* model. Here, the candidates components would be:
            # component1 (because we are working with res.partner),
            # component3 (because it has no _apply_on so apply in any case)
            self.base.component(usage='for.test')

    def test_many_components(self):
        """ Use many_components(usage=...) on the same model """
        class Component3(Component):
            _name = 'component3'
            _collection = 'collection.base'
            _usage = 'for.test'

        Component3._build_component(self.comp_registry)
        comps = self.base.many_components(usage='for.test')
        # When a component has no _apply_on, it means it can be applied
        # on *any* model. So here, both component1 and component3 match
        self.assertEqual(
            ['component1', 'component3'],
            [c._name for c in comps]
        )

    def test_many_components_other_model(self):
        """ Use many_components(usage=...) on a different model (name) """
        class Component3(Component):
            _name = 'component3'
            _collection = 'collection.base'
            _apply_on = 'res.users'
            _usage = 'for.test'

        Component3._build_component(self.comp_registry)
        comps = self.base.many_components(usage='for.test',
                                          model_name='res.users')
        self.assertEqual(
            ['component2', 'component3'],
            [c._name for c in comps]
        )

    def test_many_components_other_model_env(self):
        """ Use many_components(usage=...) on a different model (instance) """
        class Component3(Component):
            _name = 'component3'
            _collection = 'collection.base'
            _apply_on = 'res.users'
            _usage = 'for.test'

        Component3._build_component(self.comp_registry)
        comps = self.base.many_components(usage='for.test',
                                          model_name=self.env['res.users'])
        self.assertEqual(
            ['component2', 'component3'],
            [c._name for c in comps]
        )

    def test_no_component(self):
        """ No component found for asked usage """
        with self.assertRaises(NoComponentError):
            self.base.component(usage='foo')

    def test_no_many_component(self):
        """ No component found for asked usage for many_components() """
        self.assertEquals([], self.base.many_components(usage='foo'))

    def test_work_on_component(self):
        """ Check WorkContext.component() (shortcut to Component.component) """
        comp = self.work.component(usage='for.test')
        self.assertEquals('component1', comp._name)

    def test_work_on_many_components(self):
        """ Check WorkContext.many_components()

        (shortcut to Component.many_components) """
        comps = self.work.many_components(usage='for.test')
        self.assertEquals('component1', comps[0]._name)
