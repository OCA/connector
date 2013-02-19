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

from .unit.mapper import Mapper
from .unit.binder import Binder
from .unit.backend_adapter import BackendAdapter
from .unit.synchronizer import Synchronizer


class ReferenceRegistry(object):
    """ Hold a set of references """
    def __init__(self):
        self.references = set()

    def register_reference(self, reference):
        """ Register an instance of
        :py:class:`connector.reference.Reference`

        :param reference: reference to register
        :type reference: Reference
        """
        self.references.add(reference)

    def get_reference(self, service, version=None):
        """ Return an instance of
        :py:class:`connector.reference.Reference` for a
        ``service`` and a ``version``

        :param service: name of the service to return
        :type service: str
        :param version: version of the service to return
        :type version: str
        """
        for reference in self.references:
            if reference.match(service, version):
                return reference
        raise ValueError('No reference found for %s %s' %
                         (service, version))


REFERENCES = ReferenceRegistry()


def get_reference(service, version=None):
    """ Return the correct instance of
    :py:class:`connector.reference.Reference` for a
    ``service`` and a ``version``

    :param service: name of the service to return
    :type service: str
    :param version: version of the service to return
    :type version: str
    """
    return REFERENCES.get_reference(service, version)


class Reference(object):
    """ A reference represents a backend, like Magento, Prestashop,
    Redmine, ...

    .. attribute:: service

        Name of the service, for instance 'magento'

    .. attribute:: version

        The version of the service. For instance: '1.7'

    .. attribute:: parent

        A parent reference. When the reference has configuration, it
        will refer to its parent's one

    A reference knows all the classes it is able to use (mappers,
    binders, synchronizers, backend adapters) and give the appropriate
    class to use for a model. When a reference is linked to a parent and
    no particular mapper, synchronizer, backend adapter or binder is
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
        self._classes = set()
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

    def _get_class(self, base_class, *args, **kwargs):
        matching_class = None
        for cls in self.registered_classes(base_class=base_class):
            if not issubclass(cls, base_class):
                continue
            if cls.match(*args, **kwargs):
                matching_class = cls
        if matching_class is None and self.parent:
            matching_class = self.parent._get_class(base_class,
                                                    *args, **kwargs)
        return matching_class

    def get_class(self, base_class, *args, **kwargs):
        """ Find a matching subclass of `base_class` in the registered
        classes"""
        matching_class = self._get_class(base_class, *args, **kwargs)
        if matching_class is None:
            raise ValueError('No matching class found for %s '
                             'with args: %s and keyword args: %s' %
                             (base_class, args, kwargs))
        return matching_class

    def registered_classes(self, base_class=None):
        """ Yield all the classes registered on the reference

        :param base_class: select only subclasses of ``base_class``
        :type base_class: type
        """
        for cls in self._classes:
            if base_class and not issubclass(cls, base_class):
                continue
            yield cls

    def register_class(self, cls):
        """ Register a class"""
        self._classes.add(cls)

    def unregister_class(self, cls):
        """ Unregister a class"""
        self._classes.remove(cls)

    def __call__(self, cls):
        """ Reference decorator

        For a reference ``magento`` declared like this::

            magento = Reference('magento')

        A binder, synchronizer, mapper or backend adapter can be
        registered as follows::

            @magento
            class MagentoBinder(Binder):
                _model_name = 'a.model'
                # other stuff

        Thus, by doing::

            magento.get_class(Binder, 'a.model')

        We get the correct class ``MagentoBinder``.

        """
        def with_subscribe():
            self.register_class(cls)
            return cls

        return with_subscribe()
