# -*- coding: utf-8 -*-
# Copyright 2013-2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import mock
import unittest2

from odoo.addons.component.tests.common import (
    ComponentRegistryCase,
    TransactionComponentRegistryCase,
)
from odoo.addons.component.core import Component
from odoo.addons.component_event.core import EventWorkContext
from odoo.addons.component_event.components.event import (
    EventProducer,
    EventListener,
)


class TestEventWorkContext(unittest2.TestCase):
    """ Test Events Components """

    def setUp(self):
        super(TestEventWorkContext, self).setUp()
        self.env = mock.MagicMock(name='env')
        self.record = mock.MagicMock(name='record')
        self.components_registry = mock.MagicMock(name='ComponentRegistry')

    def test_env(self):
        """ WorkContext with env """
        work = EventWorkContext(model_name='res.users', env=self.env,
                                from_recordset=self.record,
                                components_registry=self.components_registry)
        self.assertEquals(self.env, work.env)
        self.assertEquals('res.users', work.model_name)
        self.assertEquals(self.record, work.from_recordset)
        with self.assertRaises(ValueError):
            work.collection

    def test_collection(self):
        """ WorkContext with collection """
        env = mock.MagicMock(name='env')
        collection = mock.MagicMock(name='collection')
        collection.env = env
        record = mock.MagicMock(name='record')
        work = EventWorkContext(model_name='res.users', collection=collection,
                                from_recordset=record,
                                components_registry=self.components_registry)
        self.assertEquals(collection, work.collection)
        self.assertEquals(record, work.from_recordset)
        self.assertEquals(env, work.env)
        self.assertEquals('res.users', work.model_name)

    def test_env_and_collection(self):
        """ WorkContext with collection and env is forbidden """
        env = mock.MagicMock(name='env')
        collection = mock.MagicMock(name='collection')
        collection.env = env
        with self.assertRaises(ValueError):
            EventWorkContext(model_name='res.users', collection=collection,
                             env=env,
                             components_registry=self.components_registry)

    def test_missing(self):
        """ WorkContext with collection and env is forbidden """
        with self.assertRaises(ValueError):
            EventWorkContext(model_name='res.users',
                             components_registry=self.components_registry)

    def test_env_work_on(self):
        """ WorkContext propagated through work_on """
        env = mock.MagicMock(name='env')
        record = mock.MagicMock(name='record')
        work = EventWorkContext(env=env, model_name='res.users',
                                from_recordset=record,
                                components_registry=self.components_registry)
        work2 = work.work_on('res.partner')
        self.assertEquals('EventWorkContext', work2.__class__.__name__)
        self.assertEquals(env, work2.env)
        self.assertEquals(record, work2.from_recordset)
        self.assertEquals('res.partner', work2.model_name)
        self.assertEquals(self.components_registry, work2.components_registry)
        with self.assertRaises(ValueError):
            work.collection

    def test_collection_work_on(self):
        """ WorkContext propagated through work_on """
        env = mock.MagicMock(name='env')
        collection = mock.MagicMock(name='collection')
        collection.env = env
        record = mock.MagicMock(name='record')
        work = EventWorkContext(collection=collection, model_name='res.users',
                                from_recordset=record,
                                components_registry=self.components_registry)
        work2 = work.work_on('res.partner')
        self.assertEquals('EventWorkContext', work2.__class__.__name__)
        self.assertEquals(collection, work2.collection)
        self.assertEquals(record, work2.from_recordset)
        self.assertEquals(env, work2.env)
        self.assertEquals('res.partner', work2.model_name)
        self.assertEquals(self.components_registry, work2.components_registry)


class TestEvent(ComponentRegistryCase):
    """ Test Events Components """

    def setUp(self):
        super(TestEvent, self).setUp()
        # build and push in the component registry the base components we
        # inherit from in the tests
        # 'base.event.producer'
        EventProducer._build_component(self.comp_registry)
        # 'base.event.listener'
        EventListener._build_component(self.comp_registry)

        # get the producer to fire the event
        # we don't mind about the collection and the model here,
        # the events we test are global
        env = mock.MagicMock()
        work = EventWorkContext(model_name='res.users', env=env,
                                components_registry=self.comp_registry)
        self.producer = self.comp_registry['base.event.producer'](work)

    def test_event(self):
        class MyEventListener(Component):
            _name = 'my.event.listener'
            _inherit = 'base.event.listener'

            def on_record_create(self, recipient, something, fields=None):
                recipient.append(('OK', something, fields))

        MyEventListener._build_component(self.comp_registry)

        something = object()
        fields = ['name', 'code']

        # as there is no return value by the event, we
        # modify this recipient to check it has been called
        recipient = []

        # collect the event and fire it
        self.producer.collect_events('on_record_create').fire(
            recipient, something, fields=fields
        )
        self.assertEquals([('OK', something, fields)], recipient)

    def test_collect_several(self):
        class MyEventListener(Component):
            _name = 'my.event.listener'
            _inherit = 'base.event.listener'

            def on_record_create(self, recipient, something, fields=None):
                recipient.append(('OK', something, fields))

        class MyOtherEventListener(Component):
            _name = 'my.other.event.listener'
            _inherit = 'base.event.listener'

            def on_record_create(self, recipient, something, fields=None):
                recipient.append(('OK', something, fields))

        MyEventListener._build_component(self.comp_registry)
        MyOtherEventListener._build_component(self.comp_registry)

        something = object()
        fields = ['name', 'code']

        # as there is no return value by the event, we
        # modify this recipient to check it has been called
        recipient = []

        # collect the event and fire them
        events = self.producer.collect_events('on_record_create')
        self.assertEquals(2, len(self.producer._events))

        events.fire(recipient, something, fields=fields)
        self.assertEquals([('OK', something, fields),
                           ('OK', something, fields)], recipient)


class TestEventRecordset(ComponentRegistryCase):
    """ Test Events with Recordset """

    def setUp(self):
        super(TestEventRecordset, self).setUp()
        # build and push in the component registry the base components we
        # inherit from in the tests
        # 'base.event.producer'
        EventProducer._build_component(self.comp_registry)
        # 'base.event.listener'
        EventListener._build_component(self.comp_registry)

        # get the producer to fire the event
        # we don't mind about the collection and the model here,
        # the events we test are global
        env = mock.MagicMock()
        self.recordset = mock.MagicMock(name='recordset')
        # when there is a 'from_recordset' in the WorkContext,
        # the listener methods will be able to access to it from
        # self.recordset. It is used when events are triggered from
        # records using BaseModel._event
        work = EventWorkContext(model_name='res.users', env=env,
                                from_recordset=self.recordset,
                                components_registry=self.comp_registry)
        self.producer = self.comp_registry['base.event.producer'](work)

    def test_event(self):
        class MyEventListener(Component):
            _name = 'my.event.listener'
            _inherit = 'base.event.listener'

            def on_foo(self, msg):
                self.recordset.msg = msg

        MyEventListener._build_component(self.comp_registry)

        # collect the event and fire it
        self.producer.collect_events('on_foo').fire('OK')
        self.assertEquals('OK', self.recordset.msg)


class TestEventFromModel(TransactionComponentRegistryCase):
    """ Test Events Components from Models """

    def setUp(self):
        super(TestEventFromModel, self).setUp()
        # build and push in the component registry the base components we
        # inherit from in the tests
        # 'base.event.producer'
        EventProducer._build_component(self.comp_registry)
        # 'base.event.listener'
        EventListener._build_component(self.comp_registry)

    def test_event_from_model(self):
        class MyEventListener(Component):
            _name = 'my.event.listener'
            _inherit = 'base.event.listener'

            def on_foo(self, name):
                self.recordset.name = name

        MyEventListener._build_component(self.comp_registry)

        partner = self.env['res.partner'].create({'name': 'test'})
        # Normally you would not pass a components_registry,
        # this is for the sake of the test, letting it empty
        # will use the global registry.
        # In a real code it would look like:
        # partner._event('on_foo').fire('bar')
        events = partner._event('on_foo',
                                components_registry=self.comp_registry)
        events.fire('bar')
        self.assertEquals('bar', partner.name)

    def test_event_filter_on_model(self):
        class GlobalListener(Component):
            _name = 'global.event.listener'
            _inherit = 'base.event.listener'

            def on_foo(self, name):
                self.recordset.name = name

        class PartnerListener(Component):
            _name = 'partner.event.listener'
            _inherit = 'base.event.listener'
            _apply_on = ['res.partner']

            def on_foo(self, name):
                self.recordset.ref = name

        class UserListener(Component):
            _name = 'user.event.listener'
            _inherit = 'base.event.listener'
            _apply_on = ['res.users']

            def on_foo(self, name):
                assert False

        self._build_components(GlobalListener, PartnerListener, UserListener)

        partner = self.env['res.partner'].create({'name': 'test'})
        partner._event('on_foo',
                       components_registry=self.comp_registry).fire('bar')
        self.assertEquals('bar', partner.name)
        self.assertEquals('bar', partner.ref)

