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

from openerp.osv import orm
from .session import ConnectorSession
from .event import (on_record_create,
                    on_record_write,
                    on_record_unlink)


create_original = orm.BaseModel.create
def create(self, cr, uid, vals, context=None):
    record_id = create_original(self, cr, uid, vals, context=context)
    if self.pool.get('connector.installed') is not None:
        session = ConnectorSession(cr, uid, context=context)
        on_record_create.fire(session, self._name, record_id, vals)
    return record_id
orm.BaseModel.create = create


write_original = orm.BaseModel.write
def write(self, cr, uid, ids, vals, context=None):
    result = write_original(self, cr, uid, ids, vals, context=context)
    if self.pool.get('connector.installed') is not None:
        if not hasattr(ids, '__iter__'):
            ids = [ids]
        session = ConnectorSession(cr, uid, context=context)
        if on_record_write.has_consumer_for(session, self._name):
            for record_id in ids:
                on_record_write.fire(session, self._name,
                                     record_id, vals)
    return result
orm.BaseModel.write = write


unlink_original = orm.BaseModel.unlink
def unlink(self, cr, uid, ids, context=None):
    if self.pool.get('connector.installed') is not None:
        if not hasattr(ids, '__iter__'):
            ids = [ids]
        session = ConnectorSession(cr, uid, context=context)
        if on_record_unlink.has_consumer_for(session, self._name):
            for record_id in ids:
                on_record_unlink.fire(session, self._name, record_id)
    return unlink_original(self, cr, uid, ids, context=context)
orm.BaseModel.unlink = unlink
