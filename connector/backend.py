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


class Backend(object):
    """ A backend represents a system to interact with,
    like Magento, Prestashop, Redmine, ...

    .. attribute:: service

        Name of the service, for instance 'magento'

    .. attribute:: version

        The version of the service. For instance: '1.7'

    .. attribute:: parent

        A parent backend. When the backend has configuration, it
        will refer to its parent's one

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
        self._classes = set()
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

    def _get_classes(self, base_class, *args, **kwargs):
        matching_classes = []
        for cls in self.registered_classes(base_class=base_class):
            if not issubclass(cls, base_class):
                continue
            if cls.match(*args, **kwargs):
                matching_classes.append(cls)
        if not matching_classes and self.parent:
            matching_classes = self.parent._get_classes(base_class,
                                                        *args, **kwargs)
        return matching_classes

    def get_class(self, base_class, *args, **kwargs):
        """ Find a matching subclass of `base_class` in the registered
        classes"""
        matching_classes = self._get_classes(base_class, *args, **kwargs)
        assert len(matching_classes) == 1, (
                'Several classes found for %s '
                'with args: %s and keyword args: %s. Found: %s' %
                (base_class, args, kwargs, matching_classes))
        assert matching_classes, ('No matching class found for %s '
                                  'with args: %s and keyword args: %s' %
                                  (base_class, args, kwargs))
        return matching_classes[0]

    def registered_classes(self, base_class=None):
        """ Yield all the classes registered on the backend

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
        """ Backend decorator

        For a backend ``magento`` declared like this::

            magento = Backend('magento')

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
