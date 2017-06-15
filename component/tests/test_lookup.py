# -*- coding: utf-8 -*-
# Copyright 2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo.addons.component.core import (
    AbstractComponent,
    Component,
)
from odoo.addons.component.exception import (
    NoComponentError,
    SeveralComponentError,
)
from .common import ComponentRegistryCase


class TestLookup(ComponentRegistryCase):

    def test_lookup_collection(self):
        class Foo(Component):
            _name = 'foo'
            _collection = 'foobar'

        class Bar(Component):
            _name = 'bar'
            _collection = 'foobar'

        class Homer(Component):
            _name = 'homer'
            _collection = 'other'

        self._build_components(Foo, Bar, Homer)

        with self.assertRaises(SeveralComponentError):
            self.comp_registry.lookup('foobar')

        components = self.comp_registry.lookup('foobar', many=True)
        self.assertEqual(
            ['foo', 'bar'],
            [c._name for c in components]
        )

    def test_lookup_usage(self):
        class Foo(Component):
            _name = 'foo'
            _collection = 'foobar'
            _usage = 'speaker'

        class Bar(Component):
            _name = 'bar'
            _collection = 'foobar'
            _usage = 'speaker'

        class Baz(Component):
            _name = 'baz'
            _collection = 'foobar'
            _usage = 'listener'

        self._build_components(Foo, Bar, Baz)

        component = self.comp_registry.lookup('foobar', usage='listener')
        self.assertEqual('baz', component._name)

        with self.assertRaises(SeveralComponentError):
            components = self.comp_registry.lookup('foobar', usage='speaker')

        components = self.comp_registry.lookup(
            'foobar', usage='speaker', many=True
        )
        self.assertEqual(
            ['foo', 'bar'],
            [c._name for c in components]
        )

    def test_lookup_no_component(self):
        with self.assertRaises(NoComponentError):
            self.comp_registry.lookup('something', usage='something')

    def test_get_by_name(self):
        class Foo(AbstractComponent):
            _name = 'foo'
            _collection = 'foobar'

        self._build_components(Foo)
        self.assertEquals('foo', self.comp_registry['foo']._name)

    def test_lookup_abstract(self):
        class Foo(AbstractComponent):
            _name = 'foo'
            _collection = 'foobar'
            _usage = 'speaker'

        class Bar(Component):
            _name = 'bar'
            _inherit = 'foo'

        self._build_components(Foo, Bar)

        comp_registry = self.comp_registry

        component = comp_registry.lookup('foobar', usage='speaker')
        self.assertEqual('bar', component._name)

        components = comp_registry.lookup('foobar', usage='speaker', many=True)
        self.assertEqual(
            ['bar'],
            [c._name for c in components]
        )

    def test_lookup_model_name(self):
        class Foo(Component):
            _name = 'foo'
            _collection = 'foobar'
            _usage = 'speaker'
            # support list
            _apply_on = ['res.partner']

        class Bar(Component):
            _name = 'bar'
            _collection = 'foobar'
            _usage = 'speaker'
            # support string
            _apply_on = 'res.users'

        class Any(Component):
            # can be used with any model as far as we look it up
            # with its usage
            _name = 'any'
            _collection = 'foobar'
            _usage = 'listener'

        self._build_components(Foo, Bar, Any)

        component = self.comp_registry.lookup('foobar',
                                              usage='speaker',
                                              model_name='res.partner')
        self.assertEqual('foo', component._name)

        component = self.comp_registry.lookup('foobar',
                                              usage='speaker',
                                              model_name='res.users')
        self.assertEqual('bar', component._name)

        component = self.comp_registry.lookup('foobar',
                                              usage='listener',
                                              model_name='res.users')
        self.assertEqual('any', component._name)
