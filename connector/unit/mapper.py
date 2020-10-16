# -*- coding: utf-8 -*-
# Copyright 2013-2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

# XXX will be removed in 11.0

"""

Mappers
=======

Mappers are the ConnectorUnit classes responsible to transform
external records into Odoo records and conversely.

"""

import logging
from contextlib import contextmanager

from ..connector import ConnectorUnit, MetaConnectorUnit, ConnectorEnvironment
from ..exception import NoConnectorUnitError

# make available from this path for backward compatibility
from ..components.mapper import mapping, changed_by, only_create  # noqa
from ..components.mapper import none, convert, m2o_to_external  # noqa
from ..components.mapper import external_to_m2o, follow_m2o_relations  # noqa
from ..components.mapper import MappingDefinition  # noqa
from ..components.mapper import MapRecord, MapOptions  # noqa

_logger = logging.getLogger(__name__)


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

        # When a class has several bases: ``class Mapper(Base1, Base2):``
        for base in bases:
            # Merge the _map_methods of the bases
            base_map_methods = getattr(base, '_map_methods', {})
            for attr_name, definition in base_map_methods.iteritems():
                if cls._map_methods.get(attr_name) is None:
                    cls._map_methods[attr_name] = definition
                else:
                    # Update the existing @changed_by with the content
                    # of each base (it is mutated in place).
                    # @only_create keeps the value defined in the first
                    # base.
                    mapping_changed_by = cls._map_methods[attr_name].changed_by
                    mapping_changed_by.update(definition.changed_by)

        # Update the _map_methods from the @mapping methods in attrs,
        # respecting the class tree.
        for attr_name, attr in attrs.iteritems():
            is_mapping = getattr(attr, 'is_mapping', None)
            if is_mapping:
                has_only_create = getattr(attr, 'only_create', False)

                mapping_changed_by = set(getattr(attr, 'changed_by', ()))
                # If already existing, it has been defined in a super
                # class, extend the @changed_by set
                if cls._map_methods.get(attr_name) is not None:
                    definition = cls._map_methods[attr_name]
                    mapping_changed_by.update(definition.changed_by)

                # keep the last choice for only_create
                definition = MappingDefinition(mapping_changed_by,
                                               has_only_create)
                cls._map_methods[attr_name] = definition
        return cls

    def __init__(cls, name, bases, attrs):
        """
        Build a ``_changed_by_fields`` list of synchronized fields with mapper.
        It takes in account the ``direct`` fields and the fields declared in
        the decorator : ``changed_by``.
        """
        changed_by_fields = set()
        if attrs.get('direct'):
            for from_attr, __ in attrs['direct']:
                attr_name = cls._direct_source_field_name(from_attr)
                changed_by_fields.add(attr_name)
        for method_name, method_def in attrs['_map_methods'].iteritems():
            changed_by_fields |= method_def[0]
        for base in bases:
            if hasattr(base, '_changed_by_fields') and base._changed_by_fields:
                changed_by_fields |= base._changed_by_fields
        cls._changed_by_fields = changed_by_fields
        super(MetaMapper, cls).__init__(name, bases, attrs)

    @staticmethod
    def _direct_source_field_name(mapping_attr):
        """ Get the mapping field name. Goes through the function modifiers.

        Ex: [(none(convert(field_name, str)), out_field_name)]

        It assumes that the modifier has ``field`` as first argument like:
            def modifier(field, args):
        """
        attr_name = mapping_attr

        if callable(mapping_attr):
            # Map the closure entries with variable names
            cells = dict(zip(
                mapping_attr.func_code.co_freevars,
                (c.cell_contents for c in mapping_attr.func_closure)))
            assert 'field' in cells, "Modifier without 'field' argument."
            if callable(cells['field']):
                attr_name = MetaMapper._direct_source_field_name(
                    cells['field'])
            else:
                attr_name = cells['field']
        return attr_name


class MapChild(ConnectorUnit):
    """ MapChild is responsible to convert items.

    Items are sub-records of a main record.
    In this example, the items are the records in ``lines``::

        sales = {'name': 'SO10',
                 'lines': [{'product_id': 1, 'quantity': 2},
                           {'product_id': 2, 'quantity': 2}]}

    A MapChild is always called from another :py:class:`Mapper` which
    provides a ``children`` configuration.

    Considering the example above, the "main" :py:class:`Mapper` would
    returns something as follows::

        {'name': 'SO10',
                 'lines': [(0, 0, {'product_id': 11, 'quantity': 2}),
                           (0, 0, {'product_id': 12, 'quantity': 2})]}

    A MapChild is responsible to:

    * Find the :py:class:`Mapper` to convert the items
    * Possibly filter out some lines (can be done by inheriting
      :py:meth:`skip_item`)
    * Convert the items' records using the found :py:class:`Mapper`
    * Format the output values to the format expected by Odoo or the
      backend (as seen above with ``(0, 0, {values})``

    A MapChild can be extended like any other
    :py:class:`~connector.connector.ConnectorUnit`.
    However, it is not mandatory to explicitly create a MapChild for
    each children mapping, the default one will be used
    (:py:class:`ImportMapChild` or :py:class:`ExportMapChild`).

    The implementation by default does not take care of the updates: if
    I import a sales order 2 times, the lines will be duplicated. This
    is not a problem as long as an importation should only support the
    creation (typical for sales orders). It can be implemented on a
    case-by-case basis by inheriting :py:meth:`get_item_values` and
    :py:meth:`format_items`.

    """
    _model_name = None

    def _child_mapper(self):
        raise NotImplementedError

    def skip_item(self, map_record):
        """ Hook to implement in sub-classes when some child
        records should be skipped.

        The parent record is accessible in ``map_record``.
        If it returns True, the current child record is skipped.

        :param map_record: record that we are converting
        :type map_record: :py:class:`MapRecord`
        """
        return False

    def get_items(self, items, parent, to_attr, options):
        """ Returns the formatted output values of items from a main record

        :param items: list of item records
        :type items: list
        :param parent: parent record
        :param to_attr: destination field (can be used for introspecting
                        the relation)
        :type to_attr: str
        :param options: dict of options, herited from the main mapper
        :return: formatted output values for the item

        """
        mapper = self._child_mapper()
        mapped = []
        for item in items:
            map_record = mapper.map_record(item, parent=parent)
            if self.skip_item(map_record):
                continue
            mapped.append(self.get_item_values(map_record, to_attr, options))
        return self.format_items(mapped)

    def get_item_values(self, map_record, to_attr, options):
        """ Get the raw values from the child Mappers for the items.

        It can be overridden for instance to:

        * Change options
        * Use a :py:class:`~connector.connector.Binder` to know if an
          item already exists to modify an existing item, rather than to
          add it

        :param map_record: record that we are converting
        :type map_record: :py:class:`MapRecord`
        :param to_attr: destination field (can be used for introspecting
                        the relation)
        :type to_attr: str
        :param options: dict of options, herited from the main mapper

        """
        return map_record.values(**options)

    def format_items(self, items_values):
        """ Format the values of the items mapped from the child Mappers.

        It can be overridden for instance to add the Odoo
        relationships commands ``(6, 0, [IDs])``, ...

        As instance, it can be modified to handle update of existing
        items: check if an 'id' has been defined by
        :py:meth:`get_item_values` then use the ``(1, ID, {values}``)
        command

        :param items_values: mapped values for the items
        :type items_values: list

        """
        return items_values


class ImportMapChild(MapChild):
    """ :py:class:`MapChild` for the Imports """

    def _child_mapper(self):
        return self.unit_for(ImportMapper)

    def format_items(self, items_values):
        """ Format the values of the items mapped from the child Mappers.

        It can be overridden for instance to add the Odoo
        relationships commands ``(6, 0, [IDs])``, ...

        As instance, it can be modified to handle update of existing
        items: check if an 'id' has been defined by
        :py:meth:`get_item_values` then use the ``(1, ID, {values}``)
        command

        :param items_values: list of values for the items to create
        :type items_values: list

        """
        return [(0, 0, values) for values in items_values]


class ExportMapChild(MapChild):
    """ :py:class:`MapChild` for the Exports """

    def _child_mapper(self):
        return self.unit_for(ExportMapper)


class Mapper(ConnectorUnit):
    """ A Mapper translates an external record to an Odoo record and
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
                ''' ``field`` is the name of the source field.

                    Naming the arg: ``field`` is required for the conversion'''
                def modifier(self, record, to_attr):
                    ''' self is the current Mapper,
                        record is the current record to map,
                        to_attr is the target field'''
                    return record[field]
                return modifier

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
                return modifier

        And used like that::

            direct = [
                    (convert('myfield', float), 'target_field'),
            ]

        More examples of modifiers:

        * :py:func:`convert`
        * :py:func:`m2o_to_external`
        * :py:func:`external_to_m2o`

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

            children = [('items', 'line_ids', 'model.name')]

        It allows to create the sales order and all its lines with the
        same call to :py:meth:`odoo.models.BaseModel.create()`.

        When using ``children`` for items of a record, we need to create
        a :py:class:`Mapper` for the model of the items, and optionally a
        :py:class:`MapChild`.

    Usage of a Mapper::

        mapper = Mapper(env)
        map_record = mapper.map_record(record)
        values = map_record.values()
        values = map_record.values(only_create=True)
        values = map_record.values(fields=['name', 'street'])

    """

    __metaclass__ = MetaMapper

    # name of the Odoo model, to be defined in concrete classes
    _model_name = None

    direct = []  # direct conversion of a field to another (from_attr, to_attr)
    children = []  # conversion of sub-records (from_attr, to_attr, model)

    _map_methods = None

    _map_child_class = None

    def __init__(self, connector_env):
        """

        :param connector_env: current environment (backend, env, ...)
        :type connector_env: :py:class:`connector.connector.Environment`
        """
        super(Mapper, self).__init__(connector_env)
        self._options = None

    def _map_direct(self, record, from_attr, to_attr):
        """ Apply the ``direct`` mappings.

        :param record: record to convert from a source to a target
        :param from_attr: name of the source attribute or a callable
        :type from_attr: callable | str
        :param to_attr: name of the target attribute
        :type to_attr: str
        """
        raise NotImplementedError

    @property
    def map_methods(self):
        """ Yield all the methods decorated with ``@mapping`` """
        for meth, definition in self._map_methods.iteritems():
            yield getattr(self, meth), definition

    def _get_map_child_unit(self, model_name):
        try:
            mapper_child = self.unit_for(self._map_child_class,
                                         model=model_name)
        except NoConnectorUnitError:
            # does not force developers to use a MapChild ->
            # will use the default one if not explicitely defined
            env = ConnectorEnvironment.create_environment(
                self.backend_record,
                model_name,
                self.connector_env
            )
            mapper_child = self._map_child_class(env)
        return mapper_child

    def _map_child(self, map_record, from_attr, to_attr, model_name):
        """ Convert items of the record as defined by children """
        assert self._map_child_class is not None, "_map_child_class required"
        child_records = map_record.source[from_attr]
        mapper_child = self._get_map_child_unit(model_name)
        items = mapper_child.get_items(child_records, map_record,
                                       to_attr, options=self.options)
        return items

    @contextmanager
    def _mapping_options(self, options):
        """ Change the mapping options for the Mapper.

        Context Manager to use in order to alter the behavior
        of the mapping, when using ``_apply`` or ``finalize``.

        """
        current = self._options
        self._options = options
        yield
        self._options = current

    @property
    def options(self):
        """ Options can be accessed in the mapping methods with
        ``self.options``. """
        return self._options

    def map_record(self, record, parent=None):
        """ Get a :py:class:`MapRecord` with record, ready to be
        converted using the current Mapper.

        :param record: record to transform
        :param parent: optional parent record, for items

        """
        return MapRecord(self, record, parent=parent)

    def _apply(self, map_record, options=None):
        """ Apply the mappings on a :py:class:`MapRecord`

        :param map_record: source record to convert
        :type map_record: :py:class:`MapRecord`

        """
        if options is None:
            options = {}
        with self._mapping_options(options):
            return self._apply_with_options(map_record)

    def _apply_with_options(self, map_record):
        """ Apply the mappings on a :py:class:`MapRecord` with
        contextual options (the ``options`` given in
        :py:meth:`MapRecord.values()` are accessible in
        ``self.options``)

        :param map_record: source record to convert
        :type map_record: :py:class:`MapRecord`

        """
        assert self.options is not None, (
            "options should be defined with '_mapping_options'")
        _logger.debug('converting record %s to model %s',
                      map_record.source, self.model)

        fields = self.options.fields
        for_create = self.options.for_create
        result = {}
        for from_attr, to_attr in self.direct:
            if callable(from_attr):
                attr_name = MetaMapper._direct_source_field_name(from_attr)
            else:
                attr_name = from_attr

            if (not fields or attr_name in fields):
                value = self._map_direct(map_record.source,
                                         from_attr,
                                         to_attr)
                result[to_attr] = value

        for meth, definition in self.map_methods:
            mapping_changed_by = definition.changed_by
            if (not fields or not mapping_changed_by or
                    mapping_changed_by.intersection(fields)):
                values = meth(map_record.source)
                if not values:
                    continue
                if not isinstance(values, dict):
                    raise ValueError('%s: invalid return value for the '
                                     'mapping method %s' % (values, meth))
                result.update(values)

        for from_attr, to_attr, model_name in self.children:
            if (not fields or from_attr in fields):
                result[to_attr] = self._map_child(map_record, from_attr,
                                                  to_attr, model_name)

        return self.finalize(map_record, result)

    def finalize(self, map_record, values):
        """ Called at the end of the mapping.

        Can be used to modify the values before returning them, as the
        ``on_change``.

        :param map_record: source map_record
        :type map_record: :py:class:`MapRecord`
        :param values: mapped values
        :returns: mapped values
        :rtype: dict
        """
        return values


class ImportMapper(Mapper):
    """ :py:class:`Mapper` for imports.

    Transform a record from a backend to an Odoo record

    """

    _map_child_class = ImportMapChild

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

        # Backward compatibility: when a field is a relation, and a modifier is
        # not used, we assume that the relation model is a binding.
        # Use an explicit modifier external_to_m2o in the 'direct' mappings to
        # change that.
        field = self.model._fields[to_attr]
        if field.type == 'many2one':
            mapping_func = external_to_m2o(from_attr)
            value = mapping_func(self, record, to_attr)
        return value


class ExportMapper(Mapper):
    """ :py:class:`Mapper` for exports.

    Transform a record from Odoo to a backend record

    """

    _map_child_class = ExportMapChild

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

        # Backward compatibility: when a field is a relation, and a modifier is
        # not used, we assume that the relation model is a binding.
        # Use an explicit modifier m2o_to_external  in the 'direct' mappings to
        # change that.
        field = self.model._fields[from_attr]
        if field.type == 'many2one':
            mapping_func = m2o_to_external(from_attr)
            value = mapping_func(self, record, to_attr)
        return value
