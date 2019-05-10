# -*- coding: utf-8 -*-
# Copyright 2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

"""
Base Model
==========

Extend the 'BaseModel' to add Events related features.


"""

from openerp import api, models
from openerp.addons.component.core import _component_databases
from openerp.addons.connector.connector import is_module_installed
from ..components.event import CollectedEvents
from ..core import EventWorkContext


@api.model
def _event(self, name, collection=None, components_registry=None):
    """ Collect events for notifications

    Usage::

        @api.multi
        def button_do_something(self):
            for record in self:
                # do something
                self._event('on_do_something').notify('something')

    With this line, every listener having a ``on_do_something`` method
    with be called and receive 'something' as argument.

    See: :mod:`..components.event`

    :param name: name of the event, start with 'on_'
    :param collection: optional collection  to filter on, only
                       listeners with similar ``_collection`` will be
                       notified
    :param components_registry: component registry for lookups,
                                mainly used for tests
    :type components_registry:
        :class:`odoo.addons.components.core.ComponentRegistry`


    """
    if not is_module_installed(self.env, 'component_event'):
        return RuntimeError("component_event not installed")
    dbname = self.env.cr.dbname
    comp_registry = (
        components_registry or _component_databases.get(dbname)
    )
    if not comp_registry or not comp_registry.ready:
        # No event should be triggered before the registry has been loaded
        # This is a very special case, when the odoo registry is being
        # built, it calls odoo.modules.loading.load_modules().
        # This function might trigger events (by writing on records, ...).
        # But at this point, the component registry is not guaranteed
        # to be ready, and anyway we should probably not trigger events
        # during the initialization. Hence we return an empty list of
        # events, the 'notify' calls will do nothing.
        return CollectedEvents([])
    if not comp_registry.get('base.event.collecter'):
        return CollectedEvents([])

    model_name = self._name
    if collection is not None:
        work = EventWorkContext(collection=collection,
                                model_name=model_name,
                                components_registry=components_registry)
    else:
        work = EventWorkContext(env=self.env, model_name=model_name,
                                components_registry=components_registry)

    collecter = work._component_class_by_name('base.event.collecter')(work)
    return collecter.collect_events(name)


models.BaseModel._event = _event


create_original = models.BaseModel.create


@api.model
@api.returns('self', lambda value: value.id)
def create(self, vals):
    record = create_original(self, vals)
    if is_module_installed(self.env, 'component_event'):
        self._event('on_record_create').notify(record, fields=vals.keys())
    return record


models.BaseModel.create = create


write_original = models.BaseModel.write


@api.multi
def write(self, vals):
    result = write_original(self, vals)
    fields = vals.keys()
    if is_module_installed(self.env, 'component_event'):
        for record in self:
            self._event('on_record_write').notify(record, fields=fields)
    return result


models.BaseModel.write = write


unlink_original = models.BaseModel.unlink


@api.multi
def unlink(self):
    if is_module_installed(self.env, 'component_event'):
        for record in self:
            self._event('on_record_unlink').notify(record)
    result = unlink_original(self)
    return result


models.BaseModel.unlink = unlink
