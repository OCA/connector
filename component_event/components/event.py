# -*- coding: utf-8 -*-
# Copyright 2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

"""
Events
======

TODO

"""

from odoo.addons.component.core import AbstractComponent, Component


class EventProducer(AbstractComponent):
    _name = 'base.event.producer'

    def __init__(self, work):
        super(EventProducer, self).__init__(work)
        self._events = set()

    def collect_events(self, name):
        component_classes = self.work._components_registry.lookup(
            usage='event.listener',
            model_name=self.model._name,
        )
        for cls in component_classes:
            if cls.has_event(name):
                component = cls(self.work)
                self._events.add(getattr(component, name))
        return self

    def fire(self, *args, **kwargs):
        for event in self._events:
            event(*args, **kwargs)


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
                    # possible future optimization: store all events in a
                    # registry so we don't need to loop on event.listener
                    # components
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
