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

from ..connector import ConnectorUnit, MetaConnectorUnit, Environment
from ..exception import MappingError
from .binder import Binder


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


class MetaMapper(MetaConnectorUnit):
    """ Metaclass for Mapper """

    def __new__(meta, name, bases, attrs):
        if attrs.get('_map_methods') is None:
            attrs['_map_methods'] = {}

        cls = super(MetaMapper, meta).__new__(meta, name, bases, attrs)

        for base in bases:
            for attr_name, changed_by in getattr(base, '_map_methods', {}).iteritems():
                cls._map_methods.setdefault(attr_name, set()).update(changed_by)

        for attr_name, attr in attrs.iteritems():
            mapping = getattr(attr, 'is_mapping', None)
            if mapping:
                changed_by = getattr(attr, 'changed_by', set())
                cls._map_methods.setdefault(attr_name, set()).update(changed_by)
        return cls


class Mapper(ConnectorUnit):
    """ Transform a record to a defined output """

    __metaclass__ = MetaMapper

    # name of the OpenERP model, to be defined in concrete classes
    _model_name = None

    direct = []  # direct conversion of a field to another (from_attr, to_attr)
    children = []  # conversion of sub-records (from_attr, to_attr, model)

    _map_methods = None

    def _map_direct(self, record, from_attr, to_attr):
        raise NotImplementedError

    def _map_children(self, record, attr, model):
        raise NotImplementedError

    @property
    def map_methods(self):
        for meth, changed_by in self._map_methods.iteritems():
            yield getattr(self, meth), changed_by

    def convert(self, record, fields=None, parent_values=None):
        """ Transform an external record to an OpenERP record or the opposite

        :param record: record to transform
        :param parent_values: openerp record of the containing object
            (e.g. sale_order for a sale_order_line)
        """
        if fields is None:
            fields = {}

        result = {}

        for from_attr, to_attr in self.direct:
            if (not fields or from_attr in fields):
                # XXX not compatible with all
                # record type (wrap
                # records in a standard class representation?)
                value = self._map_direct(record,
                                         from_attr,
                                         to_attr)
                result[to_attr] = value

        for meth, changed_by in self.map_methods:
            if changed_by.intersection(fields):
                values = meth(record)
                if not values:
                    continue
                if isinstance(values, dict):
                    result.update(values)
                else:
                    raise ValueError('%s: invalid return value for the '
                                     'mapping method %s' % (values, meth))

        for from_attr, to_attr, model in self.children:
            if (not fields or from_attr in fields):
                values = self._map_children(record, from_attr, model)
                result[to_attr] = values

        return result

    def _sub_convert(self, records, processor, parent_values=None):
        """ return values of a one2many to put in the main record
        do not create the records!
        """
        raise NotImplementedError


class ImportMapper(Mapper):
    """ Transform a record from a backend to an OpenERP record """

    def _map_direct(self, record, from_attr, to_attr):
        value = record[from_attr]
        if not value:
            return False

        column = self.model._all_columns[to_attr].column
        if column._type == 'many2one':
            rel_id = record[from_attr]
            model_name = column._obj
            env = Environment(self.backend_record,
                              self.session,
                              model_name)
            binder = env.get_connector_unit(Binder)
            value = binder.to_openerp(rel_id)

            if not value:
                raise MappingError("Can not find an existing %s for external "
                                   "record %s" % (model_name, rel_id))
        return value

    def _map_children(self, record, attr, model_name):
        env = Environment(self.backend_record,
                          self.session,
                          model_name)
        mapper = env.get_connector_unit(ImportMapper)
        child_records = record[attr]  # XXX not compatible with
                                     # all record types
        return self._sub_convert(child_records, mapper,
                                 parent_values=record)

    def _sub_convert(self, records, mapper, parent_values=None):
        """ return values of a one2many to put in the main record
        do not create the records!
        """
        result = []
        for record in records:
            vals = mapper.convert(record,
                                  parent_values=parent_values)
            result.append((0, 0, vals))
        return result


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
            env = Environment(self.backend_record,
                              self.session,
                              model_name)
            binder = env.get_connector_unit(Binder)
            value = binder.to_backend(rel_id)

            if not value:
                raise MappingError("Can not find an external id for record "
                                   "%s in model %s" % (rel_id, model_name))
        return value

    def _map_children(self, record, attr, model_name):
        env = Environment(self.backend_record,
                          self.session,
                          model_name)
        mapper = env.get_connector_unit(ExportMapper)
        child_records = record[attr]  # XXX not compatible with
                                      # all record types
        return self._sub_convert(child_records, mapper,
                                 parent_values=record)

    def _sub_convert(self, records, mapper, parent_values=None):
        """ return values of a one2many to put in the main record
        do not create the records!
        """
        result = []
        for record in records:
            vals = mapper.convert(record,
                                  parent_values=parent_values)
            result.append(vals)
        return result
