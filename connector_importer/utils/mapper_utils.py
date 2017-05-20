# -*- coding: utf-8 -*-
# Author: Simone Orsi
# Copyright 2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import pytz
from datetime import datetime

from odoo import fields

FMTS = (
    '%d/%m/%Y',
    '%d%m%Y',
    '%m/%d/%Y',
    '%Y-%m-%d',
)

FMTS_DT = (
    '%Y-%m-%d %H:%M:%S',
    '%Y-%m-%d %H:%M:%S.000'
)


def to_date(value):
    """Convert date strings to odoo format."""
    for fmt in FMTS:
        try:
            value = datetime.strptime(value, fmt).date()
            break
        except ValueError:
            pass
    if not isinstance(value, basestring):
        try:
            return fields.Date.to_string(value)
        except ValueError:
            pass
    # the value has not been converted,
    # maybe because is like 00/00/0000
    # or in another bad format
    return None


def to_utc_datetime(orig_value, tz='Europe/Rome'):
    """Convert date strings to odoo format respecting TZ."""
    value = orig_value
    local_tz = pytz.timezone('Europe/Rome')
    for fmt in FMTS_DT:
        try:
            naive = datetime.strptime(orig_value, fmt)
            local_dt = local_tz.localize(naive, is_dst=None)
            value = local_dt.astimezone(pytz.utc)
            break
        except ValueError:
            pass
    if not isinstance(value, basestring):
        return fields.Datetime.to_string(value)
    # the value has not been converted,
    # maybe because is like 00/00/0000
    # or in another bad format
    return None


def to_safe_float(value):
    """Safely convert to float."""
    if isinstance(value, float):
        return value
    if not value:
        return 0.0
    try:
        return float(value.replace(',', '.'))
    except ValueError:
        return 0.0


def to_safe_int(value):
    """Safely convert to integer."""
    if isinstance(value, int):
        return value
    if not value:
        return 0
    try:
        return int(value.replace(',', '').replace('.', ''))
    except ValueError:
        return 0


CONV_MAPPING = {
    'date': to_date,
    'safe_float': to_safe_float,
    'safe_int': to_safe_int,
}


def convert(field, conv_type,
            fallback_field=None,
            pre_value_handler=None):
    """ Convert the source field to a defined ``conv_type``
        (ex. str) before returning it.
        You can also use predefined converters like 'date'.
        Use ``fallback_field`` to provide a field of the same type
        to be used in case the base field has no value.
    """
    if conv_type in CONV_MAPPING:
        conv_type = CONV_MAPPING[conv_type]

    def modifier(self, record, to_attr):
        value = record[field]
        if not value and fallback_field:
            value = record[fallback_field]
        if pre_value_handler:
            value = pre_value_handler(value)
        if not value:
            return None
        return conv_type(value)

    return modifier


def from_mapping(field, mapping, default_value=None):
    """ Convert the source value using a ``mapping`` of values.
    """

    def modifier(self, record, to_attr):
        value = record[field]
        return mapping.get(value, default_value)

    return modifier


def concat(field, separator=' ', handler=None):
    """Concatenate values from different fields."""

    # TODO: `field` attributes is required ATM by the base mapper.
    # `_direct_source_field_name` raises and error if you don't specify it.
    # Check if we can get rid of it.

    def modifier(self, record, to_attr):
        value = [record[_field] for _field in field if record[_field].strip()]
        return separator.join(value)

    return modifier


def backend_to_rel(field,
                   search_field=None,
                   search_operator=None,
                   value_handler=None,
                   default_search_value=None,
                   default_search_field=None,
                   search_value_handler=None,
                   allowed_length=None,
                   create_missing=False,
                   create_missing_handler=None,):
    """ A modifier intended to be used on the ``direct`` mappings.

    Example::

        direct = [(backend_to_rel('country',
                    search_field='code',
                    default_search_value='IT',
                    allowed_length=2), 'country_id'),]

    :param field: name of the source field in the record
    :param search_field: name of the field to be used for searching
    :param search_operator: operator to be used for searching
    :param value_handler: a function to manipulate the raw value
    before using it. You can use it to strip out none values
    that are not none, like '0' instead of an empty string.
    :param default_search_value: if the value is none you can provide
    a default value to look up
    :param default_search_field: if the value is none you can provide
    a different field to look up for the default value
    :param search_value_handler: a callable to use
    to manipulate value before searching
    :param allowed_length: enforce a check on the search_value length
    :param create_missing: create a new record if not found
    :param create_missing_handler: provide an handler
    for getting new values for a new record to be created.
    """

    def modifier(self, record, to_attr):
        search_value = record[field]

        if search_value and value_handler:
            search_value = value_handler(record, search_value)

        # handle defaults if no search value here
        if not search_value and default_search_value:
            search_value = default_search_value
            if default_search_field:
                modifier.search_field = default_search_field

        # get the real column and the model
        column = self.model._fields[to_attr]
        rel_model = self.env[column.comodel_name]

        if allowed_length and len(search_value) != allowed_length:
            return None

        # alter search value if handler is given
        if search_value and search_value_handler:
            search_value = search_value_handler(search_value)

        if not search_value:
            return None

        # finally search it
        search_args = [(modifier.search_field,
                        modifier.search_operator,
                        search_value)]
        with self.session.change_context(active_test=False):
            value = rel_model.search(search_args)

        # create if missing
        if not value and create_missing and create_missing_handler:
            value = create_missing_handler(rel_model, record)

        # handle the final value based on col type
        if value:
            if column.type == 'many2one':
                value = value[0].id
            if column.type in ('one2many', 'many2many'):
                value = [(6, 0, [x.id for x in value])]
        else:
            return None

        return value

    # use method attributes to not mess up the variables' scope.
    # If we change the var inside modifier, without this trick
    # you get UnboundLocalError, as the variable was never defined.
    # Trick tnx to http://stackoverflow.com/a/27910553/647924
    modifier.search_field = search_field or 'name'
    modifier.search_operator = search_operator or '='

    return modifier
