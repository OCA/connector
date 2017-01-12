# -*- coding: utf-8 -*-
# Copyright 2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

# make a short api path
# odoo.addons.connector.use
def use(component_class, backend_name):
    """ Register a component in this backend

    Use as a decorator on a component, like

    ::

        @use('my.backend')
        class MyMapper(Component):
            _name = 'my.mapper'
            _inherit = 'mapper'

    """
    assert component_class and backend_name
    collection_registry.register(backend_name, component_class)
    return component_class


class CollectionRegistry(object):

    def __init__(self):
        self._backends = {}

    def register(self, backend_name, component):
        if backend_name not in self._backends:
            self._backends[backend_name] = BackendCollection()
        self._backends[backend_name].add(component)

    def find(self, backend_name, name=None, purpose=None, model_name=None,
             multi=False):
        if backend_name not in self._backends:
            return None
        return self._backends[backend_name].find(
            name=name, purpose=purpose,
            model_name=model_name,
            multi=multi,
        )


class BackendCollection(object):

    def __init__(self):
        self._components = {}

    def add(self, component):
        self._components[component._name] = component

    # TODO: add a LRU cache?
    def find(self, name=None, purpose=None, model_name=None, multi=False):
        # TODO: nice errors, complete find by purpose and model
        return self._components[name]


# TODO: handle uninstalled addons with components still in memory
# one possibility would be to check if the component exist
# in the global registry, which should not contain components
# of uninstalled addons
collection_registry = CollectionRegistry()
