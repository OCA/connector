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
from functools import partial
from collections import namedtuple

__all__ = ['get_backend', 'Backend']


class BackendRegistry(object):
    """ Hold a set of backends """
    def __init__(self):
        self.backends = set()

    def register_backend(self, backend):
        """ Register an instance of
        :py:class:`connector.backend.Backend`

        :param backend: backend to register
        :type backend: Backend
        """
        self.backends.add(backend)

    def get_backend(self, service, version=None):
        """ Return an instance of
        :py:class:`connector.backend.Backend` for a
        ``service`` and a ``version``

        :param service: name of the service to return
        :type service: str
        :param version: version of the service to return
        :type version: str
        """
        for backend in self.backends:
            if backend.match(service, version):
                return backend
        raise ValueError('No backend found for %s %s' %
                         (service, version))


BACKENDS = BackendRegistry()


def get_backend(service, version=None):
    """ Return the correct instance of
    :py:class:`connector.backend.Backend` for a
    ``service`` and a ``version``

    :param service: name of the service to return
    :type service: str
    :param version: version of the service to return
    :type version: str
    """
    return BACKENDS.get_backend(service, version)


# Represents an entry for a class in a ``Backend`` registry.
_ConnectorUnitEntry = namedtuple('_ConnectorUnitEntry',
                                 ['cls',
                                  'openerp_module',
                                  'replaced_by'])


class Backend(object):
    """ A backend represents a system to interact with,
    like Magento, Prestashop, Redmine, ...

    .. attribute:: service

        Name of the service, for instance 'magento'

    .. attribute:: version

        The version of the service. For instance: '1.7'

    .. attribute:: parent

        A parent backend. When no :py:class:`~connector.connector.ConnectorUnit`
        is found for a backend, it will search it in the `parent`.

    A backend knows all the classes it is able to use (mappers,
    binders, synchronizers, backend adapters) and give the appropriate
    class to use for a model. When a backend is linked to a parent and
    no particular mapper, synchronizer, backend adapter or binder is
    defined at its level, it will use the parent's one.

    Example::

        magento = Backend('magento')
        magento1700 = Backend(parent=magento, version='1.7')

    """

    def __init__(self, service=None, version=None, parent=None, registry=None):
        if service is None and parent is None:
            raise ValueError('A service or a parent service is expected')
        self._service = service
        self.version = version
        self.parent = parent
        self._class_entries = []
        if registry is None:
            registry = BACKENDS
        registry.register_backend(self)

    def match(self, service, version):
        """Used to find the backend for a service and a version"""
        return (self.service == service and
                self.version == version)

    @property
    def service(self):
        return self._service or self.parent.service

    def __str__(self):
        if self.version:
            return 'Backend(\'%s\', \'%s\')' % (self.service, self.version)
        return 'Backend(\'%s\')>' % self.service

    def __repr__(self):
        if self.version:
            return '<Backend \'%s\', \'%s\'>' % (self.service, self.version)
        return '<Backend \'%s\'>' % self.service

    def _get_classes(self, base_class, session, model_name):
        def follow_replacing(entries):
            candidates = set()
            for entry in entries:
                replacings = None
                if entry.replaced_by:
                    replacings = follow_replacing(entry.replaced_by)
                    if replacings:
                        candidates.update(replacings)
                # If all the classes supposed to replace the current class
                # have been discarded, the current class is a candidate.
                # It happens when the entries in 'replaced_by' are
                # in modules not installed.
                if not replacings:
                    if (session.is_module_installed(entry.openerp_module) and
                            issubclass(entry.cls, base_class) and
                            entry.cls.match(session, model_name)):
                        candidates.add(entry.cls)
            return candidates
        matching_classes = follow_replacing(self._class_entries)
        if not matching_classes and self.parent:
            matching_classes = self.parent._get_classes(base_class,
                                                        session, model_name)
        return matching_classes

    def get_class(self, base_class, session, model_name):
        """ Find a matching subclass of ``base_class`` in the registered
        classes"""
        matching_classes = self._get_classes(base_class, session,
                                             model_name)
        assert matching_classes, ('No matching class found for %s '
                                  'with session: %s, '
                                  'model name: %s' %
                                  (base_class, session, model_name))
        assert len(matching_classes) == 1, (
            'Several classes found for %s '
            'with session %s, model name: %s. Found: %s' %
            (base_class, session, model_name, matching_classes))
        return matching_classes.pop()

    def register_class(self, cls, replacing=None):
        """ Register a class"""
        def register_replace(replacing_cls):
            found = False
            for replaced_entry in self._class_entries:
                if replaced_entry.cls is replacing_cls:
                    replaced_entry.replaced_by.append(entry)
                    found = True
                    break
            if not found:
                raise ValueError('%s replaces an unregistered class: %s' %
                                 (cls, replacing))

        entry = _ConnectorUnitEntry(cls=cls,
                                    openerp_module=cls._openerp_module_,
                                    replaced_by=[])
        if replacing is not None:
            if hasattr(replacing, '__iter__'):
                for replacing_cls in replacing:
                    register_replace(replacing_cls)
            else:
                register_replace(replacing)
        self._class_entries.append(entry)

    def __call__(self, cls=None, replacing=None):
        """ Backend decorator

        For a backend ``magento`` declared like this::

            magento = Backend('magento')

        A ``ConnectorUnit`` (binder, synchronizer, mapper, ...) can be
        registered as follows::

            @magento
            class MagentoBinder(Binder):
                _model_name = 'a.model'
                # other stuff

        Thus, by doing::

            magento.get_class(Binder, 'a.model')

        We get the correct class ``MagentoBinder``.

        Any ConnectorUnit can be replaced by another doing::

            @magento(replacing=MagentoBinder)
            class MagentoBinder2(Binder):
                _model_name = 'a.model'
                # other stuff

        This is useful when working on an OpenERP module which should
        alter the original behavior of a connector.

        :param cls: the ConnectorUnit class class to register
        :type: :py:class:`connector.connector.MetaConnectorUnit`
        :param replacing: optional, the ConnectorUnit class to replace
        :type: :py:class:`connector.connector.MetaConnectorUnit`
        """
        if cls is None:
            return partial(self, replacing=replacing)

        def with_subscribe():
            self.register_class(cls, replacing=replacing)
            return cls

        return with_subscribe()
