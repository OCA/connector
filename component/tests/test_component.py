# -*- coding: utf-8 -*-
# Copyright 2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo.addons.component.core import (
    Component,
)
from .common import TransactionComponentRegistryCase
from odoo.addons.component.exception import NoComponentError


class TestComponent(TransactionComponentRegistryCase):

    def setUp(self):
        super(TestComponent, self).setUp()
        self.collection = self.env['collection.base']

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

        Component1._build_component(self.comp_registry)
        Component2._build_component(self.comp_registry)

        self.collection_record = self.collection.new()
        self.work = self.collection_record.work_on(
            'res.partner',
            # we use a custom registry only
            # for the sake of the tests
            components_registry=self.comp_registry
        )
        self.base = self.comp_registry['base'](self.work)

    def test_component_attrs(self):
        comp = self.work.components(usage='for.test')
        self.assertEquals(self.collection_record, comp.collection)
        self.assertEquals(self.work, comp.work)
        self.assertEquals(self.env, comp.env)
        self.assertEquals(self.env['res.partner'], comp.model)

    def test_component_get_by_name_same_model(self):
        comp = self.base.component_by_name('component1')
        self.assertEquals('component1', comp._name)
        self.assertEquals(self.env['res.partner'], comp.model)

    def test_component_get_by_name_other_model(self):
        comp = self.base.component_by_name(
            'component2', model_name='res.users'
        )
        self.assertEquals('component2', comp._name)
        self.assertEquals(self.env['res.users'], comp.model)

    def test_component_get_by_name_wrong_model(self):
        msg = ("Component with name 'component2' can't be used "
               "for model 'res.partner'.*")
        with self.assertRaisesRegexp(NoComponentError, msg):
            self.base.component_by_name('component2')

    def test_component_get_by_name_not_exist(self):
        msg = "No component with name 'foo' found."
        with self.assertRaisesRegexp(NoComponentError, msg):
            self.base.component_by_name('foo')

    def test_component_by_usage_same_model(self):
        comp = self.base.components(usage='for.test')
        self.assertEquals('component1', comp._name)
        self.assertEquals(self.env['res.partner'], comp.model)

    def test_component_by_usage_other_model(self):
        comp = self.base.components(usage='for.test', model_name='res.users')
        self.assertEquals('component2', comp._name)
        self.assertEquals(self.env['res.users'], comp.model)

    def test_component_by_usage_other_model_env(self):
        comp = self.base.components(usage='for.test',
                                    model_name=self.env['res.users'])
        self.assertEquals('component2', comp._name)
        self.assertEquals(self.env['res.users'], comp.model)
