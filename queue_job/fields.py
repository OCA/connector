# -*- coding: utf-8 -*-
# copyright 2016 Camptocamp
# license agpl-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import json

from odoo import fields, models


class JobSerialized(fields.Field):
    """ Serialized fields provide the storage for sparse fields. """
    type = 'job_serialized'
    column_type = ('text', 'text')

    def convert_to_column(self, value, record):
        return json.dumps(value, cls=JobEncoder)

    def convert_to_cache(self, value, record, validate=True):
        # cache format: dict
        value = value or {}
        if isinstance(value, dict):
            return value
        else:
            return json.loads(value, cls=JobDecoder, env=record.env)


class JobEncoder(json.JSONEncoder):
    """ Encode Odoo recordsets so that we can later recompose them """

    def default(self, obj):
        if isinstance(obj, models.BaseModel):
            return {'_type': 'odoo_recordset',
                    'model': obj._name,
                    'ids': obj.ids}
        return json.JSONEncoder.default(self, obj)


class JobDecoder(json.JSONDecoder):
    """ Decode json, recomposing recordsets """

    def __init__(self, *args, **kwargs):
        env = kwargs.pop('env')
        super(JobDecoder, self).__init__(
            object_hook=self.object_hook, *args, **kwargs
        )
        assert env
        self.env = env

    def object_hook(self, obj):
        if '_type' not in obj:
            return obj
        type_ = obj['_type']
        if type_ == 'odoo_recordset':
            return self.env[obj['model']].browse(obj['ids'])
        return obj
