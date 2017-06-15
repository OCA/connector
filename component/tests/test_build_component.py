# -*- coding: utf-8 -*-
# Copyright 2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import mock
from odoo.addons.component.core import Component
from .common import ComponentRegistryCase


class TestBuildComponent(ComponentRegistryCase):

    def test_no_name(self):
        class Component1(Component):
            pass

        msg = '.*must have a _name.*'
        with self.assertRaisesRegexp(TypeError, msg):
            Component1._build_component(self.comp_registry)

    def test_register(self):
        class Component1(Component):
            _name = 'component1'

        class Component2(Component):
            _name = 'component2'

        Component1._build_component(self.comp_registry)
        Component2._build_component(self.comp_registry)
        self.assertEquals(
            ['base', 'component1', 'component2'],
            list(self.comp_registry)
        )

    def test_inherit_bases(self):
        class Component1(Component):
            _name = 'component1'

        class Component2(Component):
            _inherit = 'component1'

        class Component3(Component):
            _inherit = 'component1'

        Component1._build_component(self.comp_registry)
        Component2._build_component(self.comp_registry)
        Component3._build_component(self.comp_registry)
        self.assertEquals(
            (Component3,
             Component2,
             Component1,
             self.comp_registry['base']),
            self.comp_registry['component1'].__bases__
        )

    def test_prototype_inherit_bases(self):
        class Component1(Component):
            _name = 'component1'

        class Component2(Component):
            _name = 'component2'
            _inherit = 'component1'

        class Component3(Component):
            _name = 'component3'
            _inherit = 'component1'

        class Component4(Component):
            _name = 'component4'
            _inherit = ['component2', 'component3']

        Component1._build_component(self.comp_registry)
        Component2._build_component(self.comp_registry)
        Component3._build_component(self.comp_registry)
        Component4._build_component(self.comp_registry)
        self.assertEquals(
            (Component1,
             self.comp_registry['base']),
            self.comp_registry['component1'].__bases__
        )
        self.assertEquals(
            (Component2,
             self.comp_registry['component1'],
             self.comp_registry['base']),
            self.comp_registry['component2'].__bases__
        )
        self.assertEquals(
            (Component3,
             self.comp_registry['component1'],
             self.comp_registry['base']),
            self.comp_registry['component3'].__bases__
        )
        self.assertEquals(
            (Component4,
             self.comp_registry['component2'],
             self.comp_registry['component3'],
             self.comp_registry['base']),
            self.comp_registry['component4'].__bases__
        )

    def test_custom_build(self):
        class Component1(Component):
            _name = 'component1'

            @classmethod
            def _complete_component_build(cls):
                cls._build_done = True

        Component1._build_component(self.comp_registry)
        self.assertTrue(
            self.comp_registry['component1']._build_done
        )

    def test_inherit_attrs(self):
        class Component1(Component):
            _name = 'component1'

            msg = 'ping'

            def say(self):
                return 'foo'

        class Component2(Component):
            _name = 'component2'
            _inherit = 'component1'

            msg = 'pong'

            def say(self):
                return super(Component2, self).say() + ' bar'

        Component1._build_component(self.comp_registry)
        Component2._build_component(self.comp_registry)
        component1 = self.comp_registry['component1'](mock.Mock())
        component2 = self.comp_registry['component2'](mock.Mock())
        self.assertEquals('ping', component1.msg)
        self.assertEquals('pong', component2.msg)
        self.assertEquals('foo', component1.say())
        self.assertEquals('foo bar', component2.say())

    def test_duplicate_component(self):
        class Component1(Component):
            _name = 'component1'

        class Component2(Component):
            _name = 'component1'

        Component1._build_component(self.comp_registry)
        msg = 'Component.*already exists.*'
        with self.assertRaisesRegexp(TypeError, msg):
            Component2._build_component(self.comp_registry)

    def test_no_parent(self):
        class Component1(Component):
            _name = 'component1'
            _inherit = 'component1'

        msg = 'Component.*does not exist in registry.*'
        with self.assertRaisesRegexp(TypeError, msg):
            Component1._build_component(self.comp_registry)

    def test_no_parent2(self):
        class Component1(Component):
            _name = 'component1'

        class Component2(Component):
            _name = 'component2'
            _inherit = ['component1', 'component3']

        Component1._build_component(self.comp_registry)
        msg = 'Component.*inherits from non-existing component.*'
        with self.assertRaisesRegexp(TypeError, msg):
            Component2._build_component(self.comp_registry)
