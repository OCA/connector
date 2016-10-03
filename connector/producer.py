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

"""
Producers of events.

Fire the common events:

-  ``on_record_create`` when a record is created
-  ``on_record_write`` when something is written on a record
-  ``on_record_unlink``  when a record is deleted

"""

from odoo import api, models
from .session import ConnectorSession
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
            session = ConnectorSession.from_env(self.env)
            on_record_create.fire(session, self._name, record.id, vals)
        return record

    @api.multi
    def write(self, vals):
        result = super(Base, self).write(vals)
        if is_module_installed(self.env, 'connector'):
            session = ConnectorSession.from_env(self.env)
            if on_record_write.has_consumer_for(session, self._name):
                for record_id in self.ids:
                    on_record_write.fire(session, self._name,
                                         record_id, vals)
        return result

    @api.multi
    def unlink(self):
        result = super(Base, self).unlink()
        if is_module_installed(self.env, 'connector'):
            session = ConnectorSession.from_env(self.env)
            if on_record_unlink.has_consumer_for(session, self._name):
                for record_id in self.ids:
                    on_record_unlink.fire(session, self._name, record_id)
        return result
