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

# directions
TO_REFERENCE = 'to_reference'
FROM_REFERENCE = 'from_reference'

from ..connector import ConnectorUnit, MetaConnectorUnit


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

    def __init__(cls, name, bases, attrs):
        for key, attr in attrs.iteritems():
            mapping = getattr(attr, 'is_mapping', None)
            if mapping:
                changed_by = getattr(attr, 'changed_by', None)
                if (not hasattr(cls, '_map_methods') or
                        cls._map_methods is None):
                    cls._map_methods = []
                cls._map_methods.append((attr, changed_by))


class Mapper(ConnectorUnit):
    """ Transform a record to a defined output """

    __metaclass__ = MetaMapper

    # name of the OpenERP model, to be defined in concrete classes
    _model_name = None
    # direction of the conversion (TO_REFERENCE or FROM_REFERENCE)
    direction = None

    direct = []  # direct conversion of a field to another
    method = []  # use a method to convert one or many fields
    children = []  # conversion of sub-records

    _map_methods = None

    def __init__(self, reference, session):
        super(Mapper, self).__init__(reference)
        self.session = session
        self.model = self.session.pool.get(self.model_name)

    @property
    def map_methods(self):
        return self._map_methods


class ImportMapper(Mapper):
    """ Transform a record from a backend to an OpenERP record """
    direction = FROM_REFERENCE


class ExportMapper(Mapper):
    """ Transform a record from OpenERP to a backend record """
    direction = TO_REFERENCE
