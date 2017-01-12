# -*- coding: utf-8 -*-
# Copyright 2013-2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

"""
Producers of events.

Fire the common events:

-  ``on_record_create`` when a record is created
-  ``on_record_write`` when something is written on a record
-  ``on_record_unlink``  when a record is deleted

"""

from odoo import api, models
from .event import (on_record_create,
                    on_record_write,
                    on_record_unlink)
from .connector import is_module_installed


class Base(models.AbstractModel):
    """ The base model, which is implicitly inherited by all models. """
    _inherit = 'base'

    @api.model
    @api.returns('self', lambda value: value.id)
    def create(self, vals):
        record = super(Base, self).create(vals)
        if is_module_installed(self.env, 'connector'):
            on_record_create.fire(self.env, self._name, record.id, vals)
        return record

    @api.multi
    def write(self, vals):
        result = super(Base, self).write(vals)
        if is_module_installed(self.env, 'connector'):
            if on_record_write.has_consumer_for(self.env, self._name):
                for record_id in self.ids:
                    on_record_write.fire(self.env, self._name,
                                         record_id, vals)
        return result

    @api.multi
    def unlink(self):
        result = super(Base, self).unlink()
        if is_module_installed(self.env, 'connector'):
            if on_record_unlink.has_consumer_for(self.env, self._name):
                for record_id in self.ids:
                    on_record_unlink.fire(self.env, self._name, record_id)
        return result
