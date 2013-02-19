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
    'ConnectorUnit',
    'RecordIdentifier',
]


class connectors_installed(orm.AbstractModel):
    """Empty model used to know if the module is installed on the
    database.
    """
    _name = 'connectors.installed'


class MetaConnectorUnit(type):
    """ Metaclass for ConnectorUnit """

    @property
    def model_name(cls):
        if cls._model_name is None:
            raise NotImplementedError("no _model_name for %s" % cls)
        return cls._model_name


class ConnectorUnit(object):
    """Abstract class for each piece of the connector:

    * Binder
    * Mapper
    * Synchronizer
    * Backend Adapter

    Or basically any class intended to be registered in a
    :py:class:`connector.reference.Reference`.
    """

    __metaclass__ = MetaConnectorUnit

    _model_name = None  # to be defined in sub-classes

    def __init__(self, reference):
        """
        :param reference: current reference we are working with
        :type reference: :py:class:`connector.reference.Reference`
        """
        self.reference = reference

    @classmethod
    def match(cls, model):
        """ Find the class to use """
        if hasattr(model, '_name'):  # model instance
            model_name = model._name
        else:
            model_name = model  # str
        return cls.model_name == model_name

    @property
    def model_name(self):
        if self._model_name is None:
            raise NotImplementedError('No _model_name for %s' % self)
        return self._model_name


class RecordIdentifier(object):
    """ Most of the time, on an external system, a record is identified
    by a unique ID. However occasionaly, it is identified by an ID and a
    second key, or even no ID at all but some keys.

    Instances of this class encapsulate the identifier(s) for a external
    record.

    The instance should support pickling because a
    :py:class:`RecordMetadata` can be stored in a job.
    """
    def __init__(self, **kwargs):
        for key, value in kwargs.iteritems():
            setattr(self, key, value)

    # TODO display key / values in repr
