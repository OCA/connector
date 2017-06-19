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
    EventCollecter,
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
                                components_registry=self.components_registry)
        self.assertEquals(self.env, work.env)
        self.assertEquals('res.users', work.model_name)
        with self.assertRaises(ValueError):
            work.collection  # noqa

    def test_collection(self):
        """ WorkContext with collection """
        env = mock.MagicMock(name='env')
        collection = mock.MagicMock(name='collection')
        collection.env = env
        work = EventWorkContext(model_name='res.users', collection=collection,
                                components_registry=self.components_registry)
        self.assertEquals(collection, work.collection)
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
        collection = mock.MagicMock(name='collection')
        collection.env = env
        work = EventWorkContext(env=env, model_name='res.users',
                                components_registry=self.components_registry)
        work2 = work.work_on(model_name='res.partner', collection=collection)
        self.assertEquals('WorkContext', work2.__class__.__name__)
        self.assertEquals(env, work2.env)
        self.assertEquals('res.partner', work2.model_name)
        self.assertEquals(self.components_registry, work2.components_registry)
        with self.assertRaises(ValueError):
            work.collection  # noqa

    def test_collection_work_on(self):
        """ WorkContext propagated through work_on """
        env = mock.MagicMock(name='env')
        collection = mock.MagicMock(name='collection')
        collection.env = env
        work = EventWorkContext(collection=collection, model_name='res.users',
                                components_registry=self.components_registry)
        work2 = work.work_on(model_name='res.partner')
        self.assertEquals('WorkContext', work2.__class__.__name__)
        self.assertEquals(collection, work2.collection)
        self.assertEquals(env, work2.env)
        self.assertEquals('res.partner', work2.model_name)
        self.assertEquals(self.components_registry, work2.components_registry)

    def test_collection_work_on_collection(self):
        """ WorkContext collection changed with work_on """
        env = mock.MagicMock(name='env')
        collection = mock.MagicMock(name='collection')
        collection.env = env
        work = EventWorkContext(model_name='res.users', env=env,
                                components_registry=self.components_registry)
        work2 = work.work_on(collection=collection)
        # when work_on is used inside an event component, we want
        # to switch back to a normal WorkContext, because we don't
        # need anymore the EventWorkContext
        self.assertEquals('WorkContext', work2.__class__.__name__)
        self.assertEquals(collection, work2.collection)
        self.assertEquals(env, work2.env)
        self.assertEquals('res.users', work2.model_name)
        self.assertEquals(self.components_registry, work2.components_registry)


class TestEvent(ComponentRegistryCase):
    """ Test Events Components """

    def setUp(self):
        super(TestEvent, self).setUp()
        # build and push in the component registry the base components we
        # inherit from in the tests
        # 'base.event.collecter'
        EventCollecter._build_component(self.comp_registry)
        # 'base.event.listener'
        EventListener._build_component(self.comp_registry)

        # get the collecter to notify the event
        # we don't mind about the collection and the model here,
        # the events we test are global
        env = mock.MagicMock()
        work = EventWorkContext(model_name='res.users', env=env,
                                components_registry=self.comp_registry)
        self.collecter = self.comp_registry['base.event.collecter'](work)

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

        # collect the event and notify it
        self.collecter.collect_events('on_record_create').notify(
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

        # collect the event and notify them
        collected = self.collecter.collect_events('on_record_create')
        self.assertEquals(2, len(collected.events))

        collected.notify(recipient, something, fields=fields)
        self.assertEquals([('OK', something, fields),
                           ('OK', something, fields)], recipient)

    def test_event_cache(self):
        class MyEventListener(Component):
            _name = 'my.event.listener'
            _inherit = 'base.event.listener'

            def on_record_create(self):
                pass

        MyEventListener._build_component(self.comp_registry)

        # collect the event
        collected = self.collecter.collect_events('on_record_create')
        # CollectedEvents.events contains the collected events
        self.assertEquals(1, len(collected.events))

        # build and register a new listener
        class MyOtherEventListener(Component):
            _name = 'my.other.event.listener'
            _inherit = 'base.event.listener'

            def on_record_create(self):
                pass

        MyOtherEventListener._build_component(self.comp_registry)

        # get a new collecter and check that we it finds the same
        # events even if we built a new one: it means the cache works
        env = mock.MagicMock()
        work = EventWorkContext(model_name='res.users', env=env,
                                components_registry=self.comp_registry)
        collecter = self.comp_registry['base.event.collecter'](work)
        collected = collecter.collect_events('on_record_create')
        # CollectedEvents.events contains the collected events
        self.assertEquals(1, len(collected.events))

        # if we empty the cache, as it on the class, both collecters
        # should now find the 2 events
        collecter._cache.clear()
        self.comp_registry._cache.clear()
        # CollectedEvents.events contains the collected events
        self.assertEquals(
            2,
            len(collecter.collect_events('on_record_create').events)
        )
        self.assertEquals(
            2,
            len(self.collecter.collect_events('on_record_create').events)
        )

    def test_event_cache_collection(self):
        class MyEventListener(Component):
            _name = 'my.event.listener'
            _inherit = 'base.event.listener'

            def on_record_create(self):
                pass

        MyEventListener._build_component(self.comp_registry)

        # collect the event
        collected = self.collecter.collect_events('on_record_create')
        # CollectedEvents.events contains the collected events
        self.assertEquals(1, len(collected.events))

        # build and register a new listener
        class MyOtherEventListener(Component):
            _name = 'my.other.event.listener'
            _inherit = 'base.event.listener'
            _collection = 'base.collection'

            def on_record_create(self):
                pass

        MyOtherEventListener._build_component(self.comp_registry)

        # get a new collecter and check that we it finds the same
        # events even if we built a new one: it means the cache works
        collection = mock.MagicMock(name='base.collection')
        collection._name = 'base.collection'
        collection.env = mock.MagicMock()
        work = EventWorkContext(model_name='res.users', collection=collection,
                                components_registry=self.comp_registry)
        collecter = self.comp_registry['base.event.collecter'](work)
        collected = collecter.collect_events('on_record_create')
        # for a different collection, we should not have the same
        # cache entry
        self.assertEquals(2, len(collected.events))

    def test_event_cache_model_name(self):
        class MyEventListener(Component):
            _name = 'my.event.listener'
            _inherit = 'base.event.listener'

            def on_record_create(self):
                pass

        MyEventListener._build_component(self.comp_registry)

        # collect the event
        collected = self.collecter.collect_events('on_record_create')
        # CollectedEvents.events contains the collected events
        self.assertEquals(1, len(collected.events))

        # build and register a new listener
        class MyOtherEventListener(Component):
            _name = 'my.other.event.listener'
            _inherit = 'base.event.listener'
            _apply_on = ['res.country']

            def on_record_create(self):
                pass

        MyOtherEventListener._build_component(self.comp_registry)

        # get a new collecter and check that we it finds the same
        # events even if we built a new one: it means the cache works
        env = mock.MagicMock()
        work = EventWorkContext(model_name='res.country', env=env,
                                components_registry=self.comp_registry)
        collecter = self.comp_registry['base.event.collecter'](work)
        collected = collecter.collect_events('on_record_create')
        # for a different collection, we should not have the same
        # cache entry
        self.assertEquals(2, len(collected.events))


class TestEventFromModel(TransactionComponentRegistryCase):
    """ Test Events Components from Models """

    at_install = False
    post_install = True

    def setUp(self):
        super(TestEventFromModel, self).setUp()
        # build and push in the component registry the base components we
        # inherit from in the tests
        # 'base.event.collecter'
        EventCollecter._build_component(self.comp_registry)
        # 'base.event.listener'
        EventListener._build_component(self.comp_registry)

    def test_event_from_model(self):
        class MyEventListener(Component):
            _name = 'my.event.listener'
            _inherit = 'base.event.listener'

            def on_foo(self, record, name):
                record.name = name

        MyEventListener._build_component(self.comp_registry)

        partner = self.env['res.partner'].create({'name': 'test'})
        # Normally you would not pass a components_registry,
        # this is for the sake of the test, letting it empty
        # will use the global registry.
        # In a real code it would look like:
        # partner._event('on_foo').notify('bar')
        events = partner._event('on_foo',
                                components_registry=self.comp_registry)
        events.notify(partner, 'bar')
        self.assertEquals('bar', partner.name)

    def test_event_filter_on_model(self):
        class GlobalListener(Component):
            _name = 'global.event.listener'
            _inherit = 'base.event.listener'

            def on_foo(self, record, name):
                record.name = name

        class PartnerListener(Component):
            _name = 'partner.event.listener'
            _inherit = 'base.event.listener'
            _apply_on = ['res.partner']

            def on_foo(self, record, name):
                record.ref = name

        class UserListener(Component):
            _name = 'user.event.listener'
            _inherit = 'base.event.listener'
            _apply_on = ['res.users']

            def on_foo(self, record, name):
                assert False

        self._build_components(GlobalListener, PartnerListener, UserListener)

        partner = self.env['res.partner'].create({'name': 'test'})
        partner._event(
            'on_foo',
            components_registry=self.comp_registry
        ).notify(partner, 'bar')
        self.assertEquals('bar', partner.name)
        self.assertEquals('bar', partner.ref)

    def test_event_filter_on_collection(self):
        class GlobalListener(Component):
            _name = 'global.event.listener'
            _inherit = 'base.event.listener'

            def on_foo(self, record, name):
                record.name = name

        class PartnerListener(Component):
            _name = 'partner.event.listener'
            _inherit = 'base.event.listener'
            _collection = 'collection.base'

            def on_foo(self, record, name):
                record.ref = name

        class UserListener(Component):
            _name = 'user.event.listener'
            _inherit = 'base.event.listener'
            _collection = 'magento.backend'

            def on_foo(self, record, name):
                assert False

        self._build_components(GlobalListener, PartnerListener, UserListener)

        partner = self.env['res.partner'].create({'name': 'test'})
        events = partner._event(
            'on_foo', collection=self.env['collection.base'],
            components_registry=self.comp_registry
        )
        events.notify(partner, 'bar')
        self.assertEquals('bar', partner.name)
        self.assertEquals('bar', partner.ref)