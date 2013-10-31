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


def convert(field, conv_type):
    """ A modifier intended to be used on the ``direct`` mappings.

    Convert a field's value to a given type.

    Example::

        direct = [(convert('source', str), 'target')]

    :param field: name of the source field in the record
    :param binding: True if the relation is a binding record
    """
    def modifier(self, record, to_attr):
        value = record[field]
        if not value:
            return False
        return conv_type(value)
    return transform


def m2o_to_backend(field, binding=False):
    """ A modifier intended to be used on the ``direct`` mappings.

    For a many2one, get the ID on the backend and returns it.

    When the field's relation is not a binding (i.e. it does not point to
    something like ``magento.*``), the ``binding`` argument should be False.

    Example::

        direct = [(m2o_to_backend('country_id', binding=False), 'country')]

    :param field: name of the source field in the record
    :param binding: True if the source field's relation is a binding record
    """
    def modifier(self, record, to_attr):
        if not record[field]:
            return False
        column = self.model._all_columns[field].column
        if column._type != 'many2one':
            raise ValueError('The column %s should be a many2one, got %s' %
                             field, column._type)
        rel_id = record[field].id
        model_name = column._obj
        binder = self.get_binder_for_model(model_name)
        # if a relation is not a binding, we wrap the record in the
        # binding, we'll return the id of the binding
        wrap = not binding
        value = binder.to_backend(rel_id, wrap=wrap)
        if not value:
            raise MappingError("Can not find an external id for record "
                               "%s in model %s %s wrapping" %
                               (rel_id, model_name,
                                'with' if wrap else 'without'))
        return value
    return transform


def backend_to_m2o(field, binding=False):
    """ A modifier intended to be used on the ``direct`` mappings.

    For a field from a backend which is an ID, search the corresponding
    binding in OpenERP and returns its ID.

    When the field's relation is not a binding (i.e. it does not point to
    something like ``magento.*``), the ``binding`` argument should be False.

    Example::

        direct = [(backend_to_m2o('country', binding=False), 'country_id')]

    :param field: name of the source field in the record
    :param binding: True if the target field's relation is a binding record
    """
    def modifier(self, record, to_attr):
        if not record[field]:
            return False
        column = self.model._all_columns[to_attr].column
        if column._type != 'many2one':
            raise ValueError('The column %s should be a many2one, got %s' %
                             to_attr, column._type)
        rel_id = record[field]
        model_name = column._obj
        binder = self.get_binder_for_model(model_name)
        # if we want the ID of a normal record, not a binding,
        # we ask the unwrapped id to the binder
        unwrap = not binding
        value = binder.to_openerp(rel_id, unwrap=unwrap)
        if not value:
            raise MappingError("Can not find an existing %s for external "
                               "record %s %s unwrapping" %
                               (model_name, rel_id,
                                'with' if unwrap else 'without'))
        return value
    return transform


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
    """ A Mapper translates an external record to an OpenERP record and
    conversely. The output of a Mapper is a ``dict``.

    3 types of mappings are supported:

    Direct Mappings
        Example::

            direct = [('source', 'target')]

        Here, the ``source`` field will be copied in the ``target`` field.

        A modifier can be used in the source item.
        The modifier will be applied to the source field before being
        copied in the target field.
        It should be a closure function respecting this idiom::

            def a_function(field):
                ''' ``field`` is the name of the source field '''
                def modifier(self, record, to_attr):
                    ''' self is the current Mapper,
                        record is the current record to map,
                        to_attr is the target field'''
                    return record[field]
                return transform

        And used like that::

            direct = [
                    (a_function('source'), 'target'),
            ]

        A more concrete example of modifier::

            def convert(field, conv_type):
                ''' Convert the source field to a defined ``conv_type``
                (ex. str) before returning it'''
                def modifier(self, record, to_attr):
                    value = record[field]
                    if not value:
                        return None
                    return conv_type(value)
            return transform

        And used like that::

            direct = [
                    (convert('myfield', float), 'target_field'),
            ]

        More examples of modifiers:

        * :py:func:`convert`
        * :py:func:`m2o_to_backend`
        * :py:func:`backend_to_m2o`

    Method Mappings
        A mapping method allows to execute arbitrary code and return one
        or many fields::

            @mapping
            def compute_state(self, record):
                # compute some state, using the ``record`` or not
                state = 'pending'
                return {'state': state}

        We can also specify that a mapping methods should be applied
        only when an object is created, and never applied on further
        updates::

            @only_create
            @mapping
            def default_warehouse(self, record):
                # get default warehouse
                warehouse_id = ...
                return {'warehouse_id': warehouse_id}

    Submappings
        When a record contains sub-items, like the lines of a sales order,
        we can convert the children using another Mapper::

            children = [('items', 'line_ids', LineMapper)]

    """

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

    def _init_child_mapper(self, model_name):
        raise NotImplementedError

    def _after_mapping(self, result):
        return result

    def _map_direct(self, record, from_attr, to_attr):
        """ Apply the ``direct`` mappings.

        :param record: record to convert from a source to a target
        :param from_attr: name of the source attribute or a callable
        :type from_attr: callable | str
        :param to_attr: name of the target attribute
        :type to_attr: str
        """
        raise NotImplementedError

    def _map_children(self, record, attr, model):
        raise NotImplementedError

    @property
    def map_methods(self):
        for meth, definition in self._map_methods.iteritems():
            yield getattr(self, meth), definition

    def map_record(self, record, fields=None):
        """

        :param record: recort to map
        :type record: :py:class:`~._MapperRecord`
        """
        if fields is None:
            fields = {}
        _logger.debug('mapping record %s to model %s',
                      record, self._model_name)
        data = {}
        data_for_create = {}
        children = {}
        for from_attr, to_attr in self.direct:
            if (not fields or from_attr in fields):
                value = self._map_direct(record,
                                         from_attr,
                                         to_attr)
                data[to_attr] = value

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
                    data_for_create.update(values)
                else:
                    data.update(values)

        for from_attr, to_attr, model_name in self.children:
            if (not fields or from_attr in fields):
                children[to_attr] = self._map_child(record, from_attr,
                                                    to_attr, model_name)

        return data, data_for_create, children


    def _convert(self, record, fields=None, parent_values=None):
        if fields is None:
            fields = {}

        _logger.debug('converting record %s to model %s', record, self._model_name)
        for from_attr, to_attr in self.direct:
            if (not fields or from_attr in fields):
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

    def skip_convert_child(self, record, parent_values=None):
        """ Hook to implement in sub-classes when some child
        records should be skipped.

        This method is only relevable for child mappers.

        If it returns True, the current child record is skipped."""
        return False

    # def convert_for_child(self, record, parent_values=None):
    #     """ Transform child row contained in a main record, only
    #     called from another Mapper.

    #     :param parent_values: openerp record of the containing object
    #         (e.g. sale_order for a sale_order_line)
    #     """
    #     return _MapperRecord(self, record, parent=)

    def convert(self, record, fields=None):
        """ Transform an external record to an OpenERP record or the opposite

        Sometimes we want to map values only when we create the records.
        The mapping methods have to be decorated with ``only_create`` to
        map values only for creation of records.

        :param record: record to transform
        :param fields: list of fields to convert, if empty, all fields
                       are converted
        """
        # self._convert(record, fields=fields)
        return _MapperRecord(self, record, fields=fields)

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
            if child_data:
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
            if child_data:
                result[attr] = self._format_child_rows(child_data)
        return self._after_mapping(result)

    def _format_child_rows(self, child_records):
        return child_records

    def _map_child(self, record, from_attr, model_name):
        child_records = record.source[from_attr]
        mapper = self._init_child_mapper(model_name)
        children = []
        for child_record in child_records:
            # XXX move me
            # if mapper.skip_convert_child(child_record, parent_values=record):
            #     continue
            children.append(_MapperRecord(self, record, parent=record))


class _MapperRecord(object):

    def __init__(self, mapper, source, fields=None, parent=None):
        self._source = source
        self._fields = fields
        self._mapper = mapper
        self._data = None
        self._data_for_create = None
        self._data_children = None

    @property
    def source(self):
        return self._source

    @property
    def data(self):
        if self._data is None:
            pass
        return self._data

    @property
    def data_for_create(self):
        if self._data_for_create is None:
            pass
        return self._data_for_create



class ImportMapper(Mapper):
    """ Transform a record from a backend to an OpenERP record """

    def _map_direct(self, record, from_attr, to_attr):
        """ Apply the ``direct`` mappings.

        :param record: record to convert from a source to a target
        :param from_attr: name of the source attribute or a callable
        :type from_attr: callable | str
        :param to_attr: name of the target attribute
        :type to_attr: str
        """
        if callable(from_attr):
            return from_attr(self, record, to_attr)

        value = record.get(from_attr)
        if not value:
            return False

        # may be replaced by the explicit backend_to_m2o
        column = self.model._all_columns[to_attr].column
        if column._type == 'many2one':
            mapping = backend_to_m2o(from_attr, binding=True)
            value = mapping(self, record, to_attr)
        return value

    def _init_child_mapper(self, model_name):
        env = Environment(self.backend_record,
                          self.session,
                          model_name)
        return env.get_connector_unit(ImportMapper)

    def _format_child_rows(self, child_records):
        return [(0, 0, data) for data in child_records]


class ExportMapper(Mapper):
    """ Transform a record from OpenERP to a backend record """

    def _map_direct(self, record, from_attr, to_attr):
        """ Apply the ``direct`` mappings.

        :param record: record to convert from a source to a target
        :param from_attr: name of the source attribute or a callable
        :type from_attr: callable | str
        :param to_attr: name of the target attribute
        :type to_attr: str
        """
        if callable(from_attr):
            return from_attr(self, record, to_attr)

        value = record[from_attr]
        if not value:
            return False

        # may be replaced by the explicit m2o_to_backend
        column = self.model._all_columns[from_attr].column
        if column._type == 'many2one':
            mapping = m2o_to_backend(from_attr, binding=True)
            value = mapping(self, record, to_attr)
        return value

    def _init_child_mapper(self, model_name):
        env = Environment(self.backend_record,
                          self.session,
                          model_name)
        return env.get_connector_unit(ExportMapper)
