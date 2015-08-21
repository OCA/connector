# -*- coding: utf-8 -*-
##############################################################################
#
#    Author: Guewen Baconnier
#    Copyright 2012 Camptocamp SA
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

import logging
from contextlib import contextmanager
from .deprecate import log_deprecate, DeprecatedClass

_logger = logging.getLogger(__name__)


def _get_openerp_module_name(module_path):
    """ Extract the name of the OpenERP module from the path of the
    Python module.

    Taken from OpenERP server: ``openerp.models.MetaModel``

    The (OpenERP) module name can be in the ``openerp.addons`` namespace
    or not. For instance module ``sale`` can be imported as
    ``openerp.addons.sale`` (the good way) or ``sale`` (for backward
    compatibility).
    """
    module_parts = module_path.split('.')
    if len(module_parts) > 2 and module_parts[:2] == ['openerp', 'addons']:
        module_name = module_parts[2]
    else:
        module_name = module_parts[0]
    return module_name


def install_in_connector():
    log_deprecate("This call to 'install_in_connector()' has no effect and is "
                  "not required.")


def is_module_installed(env, module_name):
    """ Check if an Odoo addon is installed.

    The function might be called before `connector` is even installed;
    in such case, `ir_module_module.is_module_installed()` is not available yet
    and this is why we first check the installation of `connector` by looking
    up for a model in the registry.

    :param module_name: name of the addon to check being 'connector' or
                        an addon depending on it

    """
    if env.registry.get('connector.backend'):
        if module_name == 'connector':
            # fast-path: connector is necessarily installed because
            # the model is in the registry
            return True
        # for another addon, check in ir.module.module
        return env['ir.module.module'].is_module_installed(module_name)

    # connector module is not installed neither any sub-addons
    return False


def get_openerp_module(cls_or_func):
    """ For a top level function or class, returns the
    name of the OpenERP module where it lives.

    So we will be able to filter them according to the modules
    installation state.
    """
    return _get_openerp_module_name(cls_or_func.__module__)


class MetaConnectorUnit(type):
    """ Metaclass for ConnectorUnit.

    Keeps a ``_module`` attribute on the classes, the same way OpenERP does
    it for the Model classes. It is then used to filter them according to
    the state of the module (installed or not).
    """

    @property
    def model_name(cls):
        log_deprecate('renamed to for_model_names')
        return cls.for_model_names

    @property
    def for_model_names(cls):
        """ Returns the list of models on which a
        :class:`~connector.connector.ConnectorUnit` is usable

        It is used in :meth:`~connector.connector.ConnectorUnit.match` when
        we search the correct ``ConnectorUnit`` for a model.

        """
        if cls._model_name is None:
            raise NotImplementedError("no _model_name for %s" % cls)
        model_name = cls._model_name
        if not hasattr(model_name, '__iter__'):
            model_name = [model_name]
        return model_name

    def __init__(cls, name, bases, attrs):
        super(MetaConnectorUnit, cls).__init__(name, bases, attrs)
        cls._openerp_module_ = get_openerp_module(cls)


class ConnectorUnit(object):
    """Abstract class for each piece of the connector:

    Examples:
        * :py:class:`connector.connector.Binder`
        * :py:class:`connector.unit.mapper.Mapper`
        * :py:class:`connector.unit.synchronizer.Synchronizer`
        * :py:class:`connector.unit.backend_adapter.BackendAdapter`

    Or basically any class intended to be registered in a
    :py:class:`~connector.backend.Backend`.
    """

    __metaclass__ = MetaConnectorUnit

    _model_name = None  # to be defined in sub-classes

    def __init__(self, connector_env):
        """

        :param connector_env: current environment (backend, session, ...)
        :type connector_env: :class:`connector.connector.ConnectorEnvironment`
        """
        super(ConnectorUnit, self).__init__()
        self.connector_env = connector_env
        self.backend = self.connector_env.backend
        self.backend_record = self.connector_env.backend_record
        self.session = self.connector_env.session

    @property
    def environment(self):
        log_deprecate('renamed to connector_env')
        return self.connector_env

    @classmethod
    def match(cls, session, model):
        """ Returns True if the current class correspond to the
        searched model.

        :param session: current session
        :type session: :py:class:`connector.session.ConnectorSession`
        :param model: model to match
        :type model: str or :py:class:`openerp.models.Model`
        """
        # filter out the ConnectorUnit from modules
        # not installed in the current DB
        if hasattr(model, '_name'):  # Model instance
            model_name = model._name
        else:
            model_name = model  # str
        return model_name in cls.for_model_names

    @property
    def env(self):
        """ Returns the openerp.api.environment """
        return self.session.env

    @property
    def model(self):
        return self.connector_env.model

    @property
    def localcontext(self):
        """ It is there for compatibility.

        :func:`openerp.tools.translate._` searches for this attribute
        in the classes do be able to translate the strings.

        There is no reason to use this attribute for other purposes.
        """
        return self.session.context

    def unit_for(self, connector_unit_class, model=None):
        """ According to the current
        :py:class:`~connector.connector.ConnectorEnvironment`,
        search and returns an instance of the
        :py:class:`~connector.connector.ConnectorUnit` for the current
        model and being a class or subclass of ``connector_unit_class``.

        If a different ``model`` is given, a new ConnectorEnvironment is built
        for this model. The class used for creating the new environment is
        the same class as in `self.connector_env` which must be
        :py:class:`~connector.connector.ConnectorEnvironment` or a subclass.

        :param connector_unit_class: ``ConnectorUnit`` to search
                                     (class or subclass)
        :type connector_unit_class: :py:class:`connector.\
                                               connector.ConnectorUnit`
        :param model: to give if the ``ConnectorUnit`` is for another
                      model than the current one
        :type model: str
        """
        if model is None or model == self.model._name:
            env = self.connector_env
        else:
            env = self.connector_env.create_environment(
                self.backend_record,
                self.session, model,
                connector_env=self.connector_env)

        return env.get_connector_unit(connector_unit_class)

    def get_connector_unit_for_model(self, connector_unit_class, model=None):
        """ Deprecated in favor of :meth:`~unit_for` """
        log_deprecate('renamed to unit_for()')
        return self.unit_for(connector_unit_class, model=model)

    def binder_for(self, model=None):
        """ Returns an new instance of the correct ``Binder`` for
        a model """
        return self.unit_for(Binder, model)

    def get_binder_for_model(self, model=None):
        """ Returns an new instance of the correct ``Binder`` for
        a model

        Deprecated, use ``binder_for`` now.
        """
        log_deprecate('renamed to binder_for()')
        return self.binder_for(model=model)


class ConnectorEnvironment(object):
    """ Environment used by the different units for the synchronization.

    .. attribute:: backend

        Current backend we are working with.
        Obtained with ``backend_record.get_backend()``.

        Instance of: :py:class:`connector.backend.Backend`

    .. attribute:: backend_record

        Browsable record of the backend. The backend is inherited
        from the model ``connector.backend`` and have at least a
        ``type`` and a ``version``.

    .. attribute:: session

        Current session we are working in. It contains the OpenERP
        cr, uid and context.

    .. attribute:: model_name

        Name of the OpenERP model to work with.

    .. attribute:: _propagate_kwargs

        List of attributes that must be used by
        :py:meth:`connector.connector.ConnectorEnvironment.create_environment`
        when a new connector environment is instantiated.
    """

    _propagate_kwargs = []

    def __init__(self, backend_record, session, model_name):
        """

        :param backend_record: browse record of the backend
        :type backend_record: :py:class:`openerp.models.Model`
        :param session: current session (cr, uid, context)
        :type session: :py:class:`connector.session.ConnectorSession`
        :param model_name: name of the model
        :type model_name: str
        """
        self.backend_record = backend_record
        backend = backend_record.get_backend()
        self.backend = backend
        self.session = session
        self.model_name = model_name

    @property
    def model(self):
        return self.env[self.model_name]

    @property
    def pool(self):
        return self.session.pool

    @property
    def env(self):
        return self.session.env

    @contextmanager
    def set_lang(self, code):
        """ Change the working language in the environment.

        It changes the ``lang`` key in the session's context.


        """
        raise DeprecationWarning('ConnectorEnvironment.set_lang has been '
                                 'deprecated. session.change_context should '
                                 'be used instead.')

    def get_connector_unit(self, base_class):
        """ Searches and returns an instance of the
        :py:class:`~connector.connector.ConnectorUnit` for the current
        model and being a class or subclass of ``base_class``.

        The returned instance is built with ``self`` for its environment.

        :param base_class: ``ConnectorUnit`` to search (class or subclass)
        :type base_class: :py:class:`connector.connector.ConnectorUnit`
        """
        return self.backend.get_class(base_class, self.session,
                                      self.model_name)(self)

    @classmethod
    def create_environment(cls, backend_record, session, model,
                           connector_env=None):
        """ Create a new environment ConnectorEnvironment.

        :param backend_record: browse record of the backend
        :type backend_record: :py:class:`openerp.models.Model`
        :param session: current session (cr, uid, context)
        :type session: :py:class:`connector.session.ConnectorSession`
        :param model_name: name of the model
        :type model_name: str
        :param connector_env: an existing environment from which the kwargs
                              will be propagated to the new one
        :type connector_env:
            :py:class:`connector.connector.ConnectorEnvironment`
        """
        kwargs = {}
        if connector_env:
            kwargs = {key: getattr(connector_env, key)
                      for key in connector_env._propagate_kwargs}
        if kwargs:
            return cls(backend_record, session, model, **kwargs)
        else:
            return cls(backend_record, session, model)

Environment = DeprecatedClass('Environment',
                              ConnectorEnvironment)


class Binder(ConnectorUnit):
    """ For one record of a model, capable to find an external or
    internal id, or create the binding (link) between them

    The Binder should be implemented in the connectors.
    """

    _model_name = None  # define in sub-classes

    def to_openerp(self, external_id, unwrap=False, browse=False):
        """ Give the OpenERP ID for an external ID

        :param external_id: external ID for which we want
                            the OpenERP ID
        :param unwrap: if True, returns the openerp_id
                       else return the id of the binding
        :param browse: if True, returns a recordset
        :return: a record ID, depending on the value of unwrap,
                 or None if the external_id is not mapped
        :rtype: int
        """
        raise NotImplementedError

    def to_backend(self, binding_id, wrap=False):
        """ Give the external ID for an OpenERP binding ID
        (ID in a model magento.*)

        :param binding_id: OpenERP binding ID for which we want the backend id
        :param wrap: if False, binding_id is the ID of the binding,
                     if True, binding_id is the ID of the normal record, the
                     method will search the corresponding binding and returns
                     the backend id of the binding
        :return: external ID of the record
        """
        raise NotImplementedError

    def bind(self, external_id, binding_id):
        """ Create the link between an external ID and an OpenERP ID

        :param external_id: external id to bind
        :param binding_id: OpenERP ID to bind
        :type binding_id: int
        """
        raise NotImplementedError

    def unwrap_binding(self, binding_id, browse=False):
        """ For a binding record, gives the normal record.

        Example: when called with a ``magento.product.product`` id,
        it will return the corresponding ``product.product`` id.

        :param browse: when True, returns a browse_record instance
                       rather than an ID
        """
        raise NotImplementedError

    def unwrap_model(self):
        """ For a binding model, gives the normal model.

        Example: when called on a binder for ``magento.product.product``,
        it will return ``product.product``.
        """
        raise NotImplementedError
