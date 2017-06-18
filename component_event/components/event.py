# -*- coding: utf-8 -*-
# Copyright 2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

"""
Events
======

TODO

"""

import logging
import operator

from odoo.addons.component.core import AbstractComponent, Component

_logger = logging.getLogger(__name__)

try:
    from cachetools import LRUCache, cachedmethod, keys
except ImportError:
    _logger.debug("Cannot import 'cachetools'.")

# Number of items we keep in LRU cache when we collect the events.
# 1 item means: for an event name, return the event methods
DEFAULT_EVENT_CACHE_SIZE = 128


class CollectedEvents(object):

    def __init__(self, events):
        self.events = events

    def notify(self, *args, **kwargs):
        for event in self.events:
            event(*args, **kwargs)


class EventCollecter(AbstractComponent):
    _name = 'base.event.collecter'

    def __init__(self, work):
        super(EventCollecter, self).__init__(work)

    @classmethod
    def _complete_component_build(cls):
        super(EventCollecter, cls)._complete_component_build()
        # the _cache being on the component class, which is
        # dynamically rebuild when odoo registry is rebuild, we
        # are sure that the result is always the same for a lookup
        # until the next rebuild of odoo's registry
        cls._cache = LRUCache(maxsize=DEFAULT_EVENT_CACHE_SIZE)

    @cachedmethod(operator.attrgetter('_cache'),
                  key=lambda self, name: keys.hashkey(
                      self.work.collection._name if self.work._collection
                      else None,
                      self.work.model_name,
                      name
                  ))
    def _collect_events(self, name):
        events = set([])
        component_classes = self.work.components_registry.lookup(
            usage='event.listener',
            model_name=self.work.model_name,
        )
        for cls in component_classes:
            if cls.has_event(name):
                component = cls(self.work)
                events.add(getattr(component, name))
        return events

    def collect_events(self, name):
        events = self._collect_events(name)
        return CollectedEvents(events)


class EventListener(AbstractComponent):
    """ Base Component for the Event listeners

    Events must be methods starting with ``on_``.

    Example: :class:`RecordsEventListener`

    Inside an event method, you can access to the record or records that
    triggered the event using ``self.recordset``.

    """
    _name = 'base.event.listener'
    _usage = 'event.listener'

    @classmethod
    def has_event(cls, name):
        return name in cls._events

    @classmethod
    def _build_event_listener_component(cls):
        events = set([])
        if not cls._abstract:
            for attr_name in dir(cls):
                if attr_name.startswith('on_'):
                    events.add(attr_name)
        cls._events = events

    @classmethod
    def _complete_component_build(cls):
        super(EventListener, cls)._complete_component_build()
        cls._build_event_listener_component()

    @property
    def recordset(self):
        """ Recordset that triggered the event """
        return getattr(self.work, 'from_recordset', None)

    # TODO: error if we don't have the collection
    def component_by_name(self, name, model_name=None):
        raise NotImplementedError

    def component(self, usage=None, model_name=None):
        raise NotImplementedError

    def many_components(self, usage=None, model_name=None):
        raise NotImplementedError


class RecordsEventListener(Component):
    _name = 'records.event.listener'
    _inherit = 'base.event.listener'

    def on_record_create(self, fields=None):
        """ Called when a record is created

        The record that triggered the event is in ``self.record``.

        """

    def on_record_write(self, fields=None):
        """ Called when a record is modified

        The record that triggered the event is in ``self.record``.

        """

    def on_record_unlink(self, fields=None):
        """ Called when a record is deleted

        The record that triggered the event is in ``self.record``.

        """
