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

# TODO multi-records:
# 2 external records may be converted in 1 openerp record and
# conversely. A processor must accept in input a dict where the keys are
# the name of the external / openerp model and the values are the
# records. And the same for the output records.
import logging
from collections import namedtuple

from ..connector import ConnectorUnit, MetaConnectorUnit, Environment
from ..exception import MappingError

_logger = logging.getLogger(__name__)


def mapping(func):
    """ Decorator declarating a mapping for a field """
    func.is_mapping = True
    return func


def changed_by(*args):
    """ Decorator for the mappings. When fields are modified, we want to modify
    only the modified fields. Using this decorator, we can specify which fields
    updates should trigger which mapping.

    If ``changed_by`` is empty, the mapping is always active.
    As far as possible, it should be used, thus, when we do an update on
    only a small number of fields on a record, the size of the output
    record will be limited to only the fields really having to be
    modified.

    :param *args: field names which trigger the mapping when modified
    """
    def register_mapping(func):
        func.changed_by = args
        return func
    return register_mapping


def only_create(func):
    """ A mapping decorated with ``only_create`` means that it has to be
    used only for the creation of the records. """
    func.only_create = True
    return func


MappingDefinition = namedtuple('MappingDefinition',
                               ['changed_by',
                                'only_create'])


class MetaMapper(MetaConnectorUnit):
    """ Metaclass for Mapper

    Build a ``_map_methods`` dict of mappings methods.
    The keys of the dict are the method names.
    The values of the dict are a namedtuple containing:
    """

    def __new__(meta, name, bases, attrs):
        if attrs.get('_map_methods') is None:
            attrs['_map_methods'] = {}

        cls = super(MetaMapper, meta).__new__(meta, name, bases, attrs)

        for base in bases:
            base_map_methods = getattr(base, '_map_methods', {})
            for attr_name, definition in base_map_methods.iteritems():
                if cls._map_methods.get(attr_name) is None:
                    cls._map_methods[attr_name] = definition
                else:
                    changed_by = cls._map_methods[attr_name].changed_by
                    changed_by.update(definition.changed_by)

        for attr_name, attr in attrs.iteritems():
            mapping = getattr(attr, 'is_mapping', None)
            if mapping:
                only_create = getattr(attr, 'only_create', False)

                changed_by = set(getattr(attr, 'changed_by', ()))
                if cls._map_methods.get(attr_name) is not None:
                    definition = cls._map_methods[attr_name]
                    changed_by.update(definition.changed_by)

                # keep the last choice for only_create
                definition = MappingDefinition(changed_by,
                                               only_create)
                cls._map_methods[attr_name] = definition
        return cls


class Mapper(ConnectorUnit):
    """ Transform a record to a defined output """

    __metaclass__ = MetaMapper

    # name of the OpenERP model, to be defined in concrete classes
    _model_name = None

    direct = []  # direct conversion of a field to another (from_attr, to_attr)
    children = []  # conversion of sub-records (from_attr, to_attr, model)

    _map_methods = None

    def __init__(self, environment):
        """

        :param environment: current environment (backend, session, ...)
        :type environment: :py:class:`connector.connector.Environment`
        """
        super(Mapper, self).__init__(environment)
        self._data = None
        self._data_for_create = None
        self._data_children = None

    def _init_child_mapper(self, model_name):
        raise NotImplementedError

    def _after_mapping(self, result):
        return result

    def _map_direct(self, record, from_attr, to_attr):
        raise NotImplementedError

    def _map_children(self, record, attr, model):
        raise NotImplementedError

    @property
    def map_methods(self):
        for meth, definition in self._map_methods.iteritems():
            yield getattr(self, meth), definition

    def _convert(self, record, fields=None, parent_values=None):
        if fields is None:
            fields = {}

        self._data = {}
        self._data_for_create = {}
        self._data_children = {}

        _logger.debug('converting record %s to model %s', record, self._model_name)
        for from_attr, to_attr in self.direct:
            if (not fields or from_attr in fields):
                # XXX not compatible with all
                # record type (wrap
                # records in a standard class representation?)
                value = self._map_direct(record,
                                         from_attr,
                                         to_attr)
                self._data[to_attr] = value

        for meth, definition in self.map_methods:
            changed_by = definition.changed_by
            if (not fields or not changed_by or
                    changed_by.intersection(fields)):
                values = meth(record)
                if not values:
                    continue
                if not isinstance(values, dict):
                    raise ValueError('%s: invalid return value for the '
                                     'mapping method %s' % (values, meth))
                if definition.only_create:
                    self._data_for_create.update(values)
                else:
                    self._data.update(values)

        for from_attr, to_attr, model_name in self.children:
            if (not fields or from_attr in fields):
                self._map_child(record, from_attr, to_attr, model_name)

    def convert_child(self, record, parent_values=None):
        """ Transform child row contained in a main record, only
        called from another Mapper.

        :param parent_values: openerp record of the containing object
            (e.g. sale_order for a sale_order_line)
        """
        self._convert(record, parent_values=parent_values)

    def convert(self, record, fields=None):
        """ Transform an external record to an OpenERP record or the opposite

        Sometimes we want to map values only when we create the records.
        The mapping methods have to be decorated with ``only_create`` to
        map values only for creation of records.

        :param record: record to transform
        :param fields: list of fields to convert, if empty, all fields
                       are converted
        """
        self._convert(record, fields=fields)

    @property
    def data(self):
        """ Returns a dict for a record processed by
        :py:meth:`~_convert` """
        if self._data is None:
            raise ValueError('Mapper.convert should be called before '
                             'accessing the data')
        result = self._data.copy()
        for attr, mappers in self._data_children.iteritems():
            child_data = [mapper.data for mapper in mappers]
            result[attr] = self._format_child_rows(child_data)
        return self._after_mapping(result)

    @property
    def data_for_create(self):
        """ Returns a dict for a record processed by
        :py:meth:`~_convert` to use only for creation of the record. """
        if self._data is None:
            raise ValueError('Mapper.convert should be called before '
                             'accessing the data')
        result = self._data.copy()
        result.update(self._data_for_create)
        for attr, mappers in self._data_children.iteritems():
            child_data = [mapper.data_for_create for mapper in mappers]
            result[attr] = self._format_child_rows(child_data)
        return self._after_mapping(result)

    def _format_child_rows(self, child_records):
        return child_records

    def _map_child(self, record, from_attr, to_attr, model_name):
        child_records = record[from_attr]
        self._data_children[to_attr] = []
        for child_record in child_records:
            mapper = self._init_child_mapper(model_name)
            mapper.convert_child(child_record, parent_values=record)
            self._data_children[to_attr].append(mapper)


class ImportMapper(Mapper):
    """ Transform a record from a backend to an OpenERP record """

    def _map_direct(self, record, from_attr, to_attr):
        value = record.get(from_attr)
        if not value:
            return False

        column = self.model._all_columns[to_attr].column
        if column._type == 'many2one':
            rel_id = record[from_attr]
            model_name = column._obj
            binder = self.get_binder_for_model(model_name)
            value = binder.to_openerp(rel_id)

            if not value:
                raise MappingError("Can not find an existing %s for external "
                                   "record %s" % (model_name, rel_id))
        return value

    def _init_child_mappers(self, model_name):
        env = Environment(self.backend_record,
                          self.session,
                          model_name)
        return env.get_connector_unit(ImportMapper)

    def _format_child_rows(self, child_records):
        return [(0, 0, data) for data in child_records]


class ExportMapper(Mapper):
    """ Transform a record from OpenERP to a backend record """

    def _map_direct(self, record, from_attr, to_attr):
        value = record[from_attr]
        if not value:
            return False

        column = self.model._all_columns[from_attr].column
        if column._type == 'many2one':
            rel_id = record[from_attr].id
            model_name = column._obj
            binder = self.get_binder_for_model(model_name)
            value = binder.to_backend(rel_id)

            if not value:
                raise MappingError("Can not find an external id for record "
                                   "%s in model %s" % (rel_id, model_name))
        return value

    def _init_child_mappers(self, model_name):
        env = Environment(self.backend_record,
                          self.session,
                          model_name)
        return env.get_connector_unit(ExportMapper)
