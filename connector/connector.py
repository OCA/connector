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

from openerp.osv import orm

__all__ = [
    'Environment',
    'ConnectorUnit',
]


class connector_installed(orm.AbstractModel):
    """Empty model used to know if the module is installed on the
    database.

    If the model is in the registry, the module is installed.
    """
    _name = 'connector.installed'


class MetaConnectorUnit(type):
    """ Metaclass for ConnectorUnit """

    @property
    def model_name(cls):
        if cls._model_name is None:
            raise NotImplementedError("no _model_name for %s" % cls)
        model_name = cls._model_name
        if not hasattr(model_name, '__iter__'):
            model_name = [model_name]
        return model_name


class ConnectorUnit(object):
    """Abstract class for each piece of the connector:

    * Binder
    * Mapper
    * Synchronizer
    * Backend Adapter

    Or basically any class intended to be registered in a
    :py:class:`connector.backend.Backend`.
    """

    __metaclass__ = MetaConnectorUnit

    _model_name = None  # to be defined in sub-classes

    def __init__(self, environment):
        """

        :param environment: current environment (backend, session, ...)
        :type environment: :py:class:`connector.connector.Environment`
        """
        self.environment = environment
        self.backend = self.environment.backend
        self.backend_record = self.environment.backend_record
        self.session = self.environment.session
        self.model = self.session.pool.get(environment.model_name)

    @classmethod
    def match(cls, model):
        """ Find the class to use """
        if hasattr(model, '_name'):  # Model instance
            model_name = model._name
        else:
            model_name = model  # str
        return model_name in cls.model_name

    def get_connector_unit_for_model(self, connector_unit_class, model=None):
        if model is None:
            env = self.environment
        else:
            env = Environment(self.backend_record,
                              self.session,
                              model)
        return env.get_connector_unit(connector_unit_class)


    def get_binder_for_model(self, model=None):
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
        """ Change the working language in the environment. """
        self.session.context['lang'] = code

    def get_connector_unit(self, base_class, *args, **kwargs):
        """ Search the class using
        :py:class:`connector.backend.Backend.get_class`,
        return an instance of the class with ``self`` as environment.

        The ``model_name`` should not be passed in the arguments as
        ``self.model_name`` is used.
        """
        return self.backend.get_class(base_class, self.model_name,
                                      *args, **kwargs)(self)


class Binder(ConnectorUnit):
    """ For one record of a model, capable to find an external or
    internal id, or create the link between them
    """

    _model_name = None  # define in sub-classes

    def to_openerp(self, external_id, unwrap=False):
        """ Give the OpenERP ID for an external ID

        :param external_id: external ID for which we want
                                   the OpenERP ID
        :param unwrap: if True, returns the openerp_id of the
                       magento_xxxx record, else return the id (binding id)
                       of that record
        :return: a record ID, depending on the value of unwrap,
                 or None if the external_id is not mapped
        :rtype: int
        """
        raise NotImplementedError

    def to_backend(self, binding_id):
        """ Give the external ID for an OpenERP ID (binding id, from a
        magento.* model)

        :param binding_id: OpenERP ID for which we want the backend id
        :return: external ID of the record
        """
        raise NotImplementedError

    def bind(self, external_id, binding_id, metadata=None):
        """ Create the link between an external ID and an OpenERP ID

        :param external_id: external id to bind
        :param binding_id: OpenERP ID to bind
        :type binding_id: int
        :param metadata: optional values to store on the relation model
        :type metadata: dict
        """
        raise NotImplementedError
