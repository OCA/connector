# -*- coding: utf-8 -*-
##############################################################################
#
#    Author: Guewen Baconnier
#    Copyright 2013 Camptocamp SA
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from .mapper import Mapper
from .binder import Binder
from .backend_adapter import BackendAdapter
from .synchronizer import Synchronizer


class ReferenceRegistry(object):
    """ Hold a set of references """
    def __init__(self):
        self.references = set()

    def register_reference(self, reference):
        self.references.add(reference)

    def get_reference(self, service, version=None):
        for reference in self.references:
            if reference.match(service, version):
                return reference
        raise ValueError('No reference found for %s %s' %
                         (service, version))


REFERENCES = ReferenceRegistry()


def get_reference(service, version=None):
    """ Return the correct instance of a `Reference` for a
    ``service`` and a ``version``
    """
    return REFERENCES.get_reference(service, version)


class Reference(object):
    """ A reference represents a backend like Magento, Prestashop,
    Redmine, ...

    .. attribute:: service

        Name of the service, for instance 'magento'

    .. attribute:: version

        The version of the service. For instance: '1.7'

    .. attribute:: parent

        A parent reference. When the reference has configuration, it
        will refer to its parent's one

    The references contain all the classes they are able to use
    (mappers, binders, synchronizers, backend adapters) and give the
    appropriate class to use for a model. When a reference is linked to
    a parent and no particular mapper, synchronizer or binder is
    defined at its level, it will use the parent's one.

    Example::

        magento = Reference('magento')
        magento1700 = Reference(parent=magento, version='1.7')

    """

    def __init__(self, service=None, version=None, parent=None, registry=None):
        if service is None and parent is None:
            raise ValueError('A service or a parent service is expected')
        self._service = service
        self.version = version
        self.parent = parent
        self._mappers = set()
        self._binders = set()
        self._synchronizers = set()
        self._backend_adapters = set()
        if registry is None:
            registry = REFERENCES
        registry.register_reference(self)

    def match(self, service, version):
        """Used to find the reference for a service and a version"""
        return (self.service == service and
                self.version == version)

    @property
    def service(self):
        return self._service or self.parent.service

    def __str__(self):
        if self.version:
            return 'Reference(\'%s\', \'%s\')' % (self.service, self.version)
        return 'Reference(\'%s\')>' % self.service

    def __repr__(self):
        if self.version:
            return '<Reference \'%s\', \'%s\'>' % (self.service, self.version)
        return '<Reference \'%s\'>' % self.service

    def _get_class(self, attr_name, *args):
        utility_class = None
        for cls in getattr(self, attr_name):
            if cls.match(*args):
                utility_class = cls
        if utility_class is None and self.parent:
            utility_class = self.parent._get_class(attr_name, *args)
        return utility_class

    def get_synchronizer(self, model, synchro_type):
        synchronizer = self._get_class('_synchronizers', model, synchro_type)
        if synchronizer is None:
            raise ValueError('No matching synchronizer found for %s '
                             'with model: %s, synchronization_type: %s' %
                             (self, model, synchro_type))
        return synchronizer

    def get_mapper(self, model, direction):
        mapper = self._get_class('_mappers', model, direction)
        if mapper is None:
            raise ValueError('No matching mapper found for %s '
                             'with model, direction: %s, %s' %
                             (self, model, direction))
        return mapper

    def get_backend_adapter(self, model):
        adapter = self._get_class('_backend_adapters', model)
        if adapter is None:
            raise ValueError('No matching backend adapter found for %s '
                             'with model: %s' % (self, model))
        return adapter

    def get_binder(self, model):
        binder = self._get_class('_binders', model)
        if binder is None:
            raise ValueError('No matching binder found for %s '
                             'with model: %s' % (self, model))
        return binder

    def register_binder(self, binder):
        self._binders.add(binder)

    def register_synchronizer(self, synchronizer):
        self._synchronizers.add(synchronizer)

    def register_mapper(self, mapper):
        self._mappers.add(mapper)

    def register_backend_adapter(self, adapter):
        self._backend_adapters.add(adapter)

    def unregister_binder(self, binder):
        self._binders.remove(binder)

    def unregister_synchronizer(self, synchronizer):
        self._synchronizers.remove(synchronizer)

    def unregister_mapper(self, mapper):
        self._mappers.remove(mapper)

    def unregister_backend_adapter(self, adapter):
        self._backend_adapters.remove(adapter)

    def __call__(self, cls):
        """ Reference decorator

        For a reference ``magento`` declared like this::

            magento = Reference('magento')

        A binder, synchronizer, mapper or backend adapter can be
        subscribed as follows::

            @magento
            class MagentoBinder(Binder):
                # do stuff

        """
        def with_subscribe():
            if issubclass(cls, Binder):
                self.register_binder(cls)
            elif issubclass(cls, Synchronizer):
                self.register_synchronizer(cls)
            elif issubclass(cls, Mapper):
                self.register_mapper(cls)
            elif issubclass(cls, BackendAdapter):
                self.register_backend_adapter(cls)
            else:
                raise TypeError(
                        '%s is not a valid type for %s.\n'
                        'Allowed types are subclasses of Binder, '
                        ' Synchronizer, Mapper, BackendAdapter' %
                        (cls, self))
            return cls

        return with_subscribe()
