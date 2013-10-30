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

import inspect
from openerp.osv import orm


def _get_openerp_module_name(module_path):
    """ Extract the name of the OpenERP module from the path of the
    Python module.

    Taken from OpenERP server: ``openerp.osv.orm``

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
    """ Installs an OpenERP module in the ``Connector`` framework.

    It has to be called once per OpenERP module to plug.

    Under the cover, it creates a ``orm.AbstractModel`` whose name is
    the name of the module with a ``.intalled`` suffix:
    ``{name_of_the_openerp_module_to_install}.installed``.

    The connector then uses this model to know when the OpenERP module
    is installed or not and whether it should use the ConnectorUnit
    classes of this module or not and whether it should fire the
    consumers of events or not.
    """
    # Get the module of the caller
    module = inspect.getmodule(inspect.currentframe().f_back)
    openerp_module_name = _get_openerp_module_name(module.__name__)
    # Build a new AbstractModel with the name of the module and the suffix
    name = "%s.installed" % openerp_module_name
    class_name = name.replace('.', '_')
    # we need to call __new__ and __init__ in 2 phases because
    # __init__ needs to have the right __module__ and _module attributes
    model = orm.MetaModel.__new__(orm.MetaModel, class_name,
                                  (orm.AbstractModel,), {'_name': name})
    # Update the module of the model, it should be the caller's one
    model._module = openerp_module_name
    model.__module__ = module.__name__
    orm.MetaModel.__init__(model, class_name,
                           (orm.AbstractModel,), {'_name': name})


# install the connector itself
install_in_connector()


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
        """
        The ``model_name`` is used to find the class and is mandatory for
        :py:class:`~connector.connector.ConnectorUnit` which are registered
        on a :py:class:`~connector.backend.Backend`.
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

    def __init__(self, environment):
        """

        :param environment: current environment (backend, session, ...)
        :type environment: :py:class:`connector.connector.Environment`
        """
        super(ConnectorUnit, self).__init__()
        self.environment = environment
        self.backend = self.environment.backend
        self.backend_record = self.environment.backend_record
        self.session = self.environment.session
        self.model = self.session.pool.get(environment.model_name)
        # so we can use openerp.tools.translate._, used to find the lang
        # that's because _() search for a localcontext attribute
        # but self.localcontext should not be used for other purposes
        self.localcontext = self.session.context

    @classmethod
    def match(cls, session, model):
        """ Returns True if the current class correspond to the
        searched model.

        :param session: current session
        :type session: :py:class:`connector.session.ConnectorSession`
        :param model: model to match
        :type model: str or :py:class:`openerp.osv.orm.Model`
        """
        # filter out the ConnectorUnit from modules
        # not installed in the current DB
        if hasattr(model, '_name'):  # Model instance
            model_name = model._name
        else:
            model_name = model  # str
        return model_name in cls.model_name

    def get_connector_unit_for_model(self, connector_unit_class, model=None):
        """ According to the current
        :py:class:`~connector.connector.Environment`,
        search and returns an instance of the
        :py:class:`~connector.connector.ConnectorUnit` for the current
        model and being a class or subclass of ``connector_unit_class``.

        If a ``model`` is given, a new
        :py:class:`~connector.connector.Environment`
        is built for this model.

        :param connector_unit_class: ``ConnectorUnit`` to search (class or subclass)
        :type connector_unit_class: :py:class:`connector.connector.ConnectorUnit`
        :param model: to give if the ``ConnectorUnit`` is for another
                      model than the current one
        :type model: str
        """
        if model is None:
            env = self.environment
        else:
            env = Environment(self.backend_record,
                              self.session,
                              model)
        return env.get_connector_unit(connector_unit_class)

    def get_binder_for_model(self, model=None):
        """ Returns an new instance of the correct ``Binder`` for
        a model """
        return self.get_connector_unit_for_model(Binder, model)


class Environment(object):
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
    """

    def __init__(self, backend_record, session, model_name):
        """

        :param backend_record: browse record of the backend
        :type backend_record: :py:class:`openerp.osv.orm.browse_record`
        :param session: current session (cr, uid, context)
        :type session: :py:class:`connector.session.ConnectorSession`
        :param model_name: name of the model
        :type model_name: str
        """
        self.backend_record = backend_record
        self.backend = backend_record.get_backend()
        self.session = session
        self.model_name = model_name
        self.model = self.session.pool.get(model_name)
        self.pool = self.session.pool

    def set_lang(self, code):
        """ Change the working language in the environment.

        It changes the ``lang`` key in the session's context.
        """
        self.session.context['lang'] = code

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


class Binder(ConnectorUnit):
    """ For one record of a model, capable to find an external or
    internal id, or create the binding (link) between them

    The Binder should be implemented in the connectors.
    """

    _model_name = None  # define in sub-classes

    def to_openerp(self, external_id, unwrap=False):
        """ Give the OpenERP ID for an external ID

        :param external_id: external ID for which we want
                            the OpenERP ID
        :param unwrap: if True, returns the openerp_id
                       else return the id of the binding
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
