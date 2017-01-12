# -*- coding: utf-8 -*-
# Copyright 2013-2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from functools import partial
from collections import namedtuple
from .exception import NoConnectorUnitError
from .connector import is_module_installed

__all__ = ['Backend']


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
                                  'odoo_module',
                                  'replaced_by'])


class Backend(object):
    """ A backend represents a system to interact with,
    like Magento, Prestashop, Redmine, ...

    It owns 3 properties:

    .. attribute:: service

        Name of the service, for instance 'magento'

    .. attribute:: version

        The version of the service. For instance: '1.7'

    .. attribute:: parent

        A parent backend.
        When no :py:class:`~connector.connector.ConnectorUnit`
        is found for a backend, it will search it in the `parent`.

    The Backends structure is a key part of the framework,
    but is rather simple.

    * A ``Backend`` instance holds a registry of
      :py:class:`~connector.connector.ConnectorUnit` classes
    * It can return the appropriate
      :py:class:`~connector.connector.ConnectorUnit` to use for a task
    * If no :py:class:`~connector.connector.ConnectorUnit` is registered for a
      task, it will ask it to its direct parent (and so on)


    The Backends support 2 different extension mechanisms. One is more
    vertical - across the versions - and the other would be more horizontal as
    it allows to modify the behavior for 1 version of backend.

    For the sake of the example, let's say we have theses backend versions::

                 <Magento>
                     |
              -----------------
              |               |
        <Magento 1.7>   <Magento 2.0>
              |
        <Magento with specific>

    And here is the way they are declared in Python::

        magento = Backend('magento')
        magento1700 = Backend(parent=magento, version='1.7')
        magento2000 = Backend(parent=magento, version='2.0')

        magento_specific = Backend(parent=magento1700, version='1.7-specific')

    In the graph above, ``<Magento>`` will hold all the classes shared between
    all the versions.  Each Magento version (``<Magento 1.7>``, ``<Magento
    2.0>``) will use the classes defined on ``<Magento>``, excepted if they
    registered their own ones instead. That's the same for ``<Magento with
    specific>`` but this one contains customizations which are specific to an
    instance (typically you want specific mappings for one instance).

    Here is how you would register classes on ``<Magento>`` and another on
    ``<Magento 1.7>``::

        @magento
        class Synchronizer(ConnectorUnit):
            _model_name = 'res.partner'

        @magento
        class Mapper(ConnectorUnit):
            _model_name = 'res.partner'

        @magento1700
        class Synchronizer1700(Synchronizer):
            _model_name = 'res.partner'

    Here, the :py:meth:`~get_class` called on ``magento1700`` would return::

        magento1700.get_class(Synchronizer, env, 'res.partner')
        # => Synchronizer1700
        magento1700.get_class(Mapper, env, 'res.partner')
        # => Mapper

    This is the vertical extension mechanism, it says that each child version
    is able to extend or replace the behavior of its parent.

    .. note:: when using the framework, you won't need to call
    :py:meth:`~get_class`, usually, you will call
    :py:meth:`connector.connector.ConnectorEnvironment.get_connector_unit`.

    The vertical extension is the one you will probably use the most, because
    most of the things you will change concern your custom adaptations or
    different behaviors between the versions of the backend.

    However, some time, we need to change the behavior of a connector, by
    installing an addon. For example, say that we already have an
    ``ImportMapper`` for the products in the Magento Connector. We create a
    - generic - addon to handle the catalog in a more advanced manner. We
    redefine an ``AdvancedImportMapper``, which should be used when the
    addon is installed. This is the horizontal extension mechanism.

    Replace a :py:class:`~connector.connector.ConnectorUnit` by another one
    in a backend::

        @backend(replacing=ImportMapper)
        class AdvancedImportMapper(ImportMapper):
            _model_name = 'product.product'

    .. warning:: The horizontal extension should be used sparingly and
                 cautiously since as soon as 2 addons want to replace
                 the same class, you'll have a conflict
                 (which would need to create a third addon to glue
                 them, ``replacing`` can take a tuple of classes to replace
                 and this is exponential).
                 This mechanism should be used only in some well placed
                 circumstances for generic addons.
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
        return 'Backend(\'%s\')' % self.service

    def __repr__(self):
        if self.version:
            return '<Backend \'%s\', \'%s\'>' % (self.service, self.version)
        return '<Backend \'%s\'>' % self.service

    def _get_classes(self, base_class, env, model_name):
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
                    if (is_module_installed(env, entry.odoo_module) and
                            issubclass(entry.cls, base_class) and
                            entry.cls.match(env, model_name)):
                        candidates.add(entry.cls)
            return candidates
        matching_classes = follow_replacing(self._class_entries)
        if not matching_classes and self.parent:
            matching_classes = self.parent._get_classes(base_class,
                                                        env, model_name)
        return matching_classes

    def get_class(self, base_class, env, model_name):
        """ Find a matching subclass of ``base_class`` in the registered
        classes.

        :param base_class: class (and its subclass) to search in the registry
        :type base_class: :py:class:`connector.connector.MetaConnectorUnit`
        :param env: current env
        :type env: :py:class:`odoo.api.EnvironmentError`
        """
        matching_classes = self._get_classes(base_class, env,
                                             model_name)
        if not matching_classes:
            raise NoConnectorUnitError('No matching class found for %s '
                                       'model name: %s' %
                                       (base_class, model_name))

        assert len(matching_classes) == 1, (
            'Several classes found for %s '
            'with model name: %s. Found: %s' %
            (base_class, model_name, matching_classes))
        return matching_classes.pop()

    def register_class(self, cls, replacing=None):
        """ Register a class in the backend.

        :param cls: the ConnectorUnit class class to register
        :type cls: :py:class:`connector.connector.MetaConnectorUnit`
        :param replacing: optional, the ConnectorUnit class to replace
        :type replacing: :py:class:`connector.connector.MetaConnectorUnit`
        """
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
                                    odoo_module=cls._module,
                                    replaced_by=[])
        if replacing is not None:
            if replacing is cls:
                raise ValueError('%r cannot replace itself' % replacing)
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

        A :py:class:`connector.connector.ConnectorUnit`
        (like a binder, a synchronizer, a mapper, ...) can be
        registered as follows::

            @magento
            class MagentoBinder(Binder):
                _model_name = 'a.model'
                # other stuff

        Thus, by doing::

            magento.get_class(Binder, 'a.model')

        We get the correct class ``MagentoBinder``.

        Any ``ConnectorUnit`` can be replaced by another doing::

            @magento(replacing=MagentoBinder)
            class MagentoBinder2(Binder):
                _model_name = 'a.model'
                # other stuff

        This is useful when working on an Odoo module which should
        alter the original behavior of a connector for an existing backend.

        :param cls: the ConnectorUnit class class to register
        :type cls: :py:class:`connector.connector.MetaConnectorUnit`
        :param replacing: optional, the ConnectorUnit class to replace
        :type replacing: :py:class:`connector.connector.MetaConnectorUnit`
        """
        if cls is None:
            return partial(self, replacing=replacing)

        def with_subscribe():
            self.register_class(cls, replacing=replacing)
            return cls

        return with_subscribe()
