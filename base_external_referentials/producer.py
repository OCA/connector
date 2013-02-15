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
                    on_record_unlink,
                    on_workflow_signal)

# monkey patch appproach

create_original = orm.Model.create
def create(self, cr, uid, vals, context=None):
    record_id = create_original(self, cr, uid, vals, context=context)
    session = ConnectorSession(cr, uid, context=context)
    on_record_create.fire(self._name, session, record_id)
    return record_id
orm.Model.create = create


write_original = orm.Model.write
def write(self, cr, uid, ids, vals, context=None):
    result = write_original(self, cr, uid, ids, vals, context=context)
    if not hasattr(ids, '__iter__'):
        ids = [ids]
    session = ConnectorSession(cr, uid, context=context)
    for record_id in ids:
        on_record_write.fire(self._name, session, record_id, vals.keys())
    return result
orm.Model.write = write


unlink_original = orm.Model.unlink
def unlink(self, cr, uid, ids, context=None):
    result = unlink_original(self, cr, uid, ids, context=context)
    if not hasattr(ids, '__iter__'):
        ids = [ids]
    session = ConnectorSession(cr, uid, context=context)
    for record_id in ids:
        on_record_unlink.fire(self._name, session, record_id)
    return result
orm.Model.unlink = unlink



# _inherit approach. need to call add_events on the models
# which should have events
def add_events(model_name):
    """ Return a class which inherit the model ``model_name``

    This _inherit'ed class fires the ``on_record_create``,
    ``on_record_write``, ``on_record_unlink`` events.
    """
    class_name = model_name.replace('.', '_')
    inherit_class = type(class_name,
                         (orm.Model,),
                         {'_inherit': model_name})

    def create(self, cr, uid, vals, context=None):
        record_id = super(inherit_class, self).create(cr, uid, vals,
                                                      context=context)
        session = ConnectorSession(cr, uid, context=context)
        on_record_create.fire(self._name, session, record_id)
        return record_id

    def write(self, cr, uid, ids, vals, context=None):
        result = super(inherit_class, self).write(cr, uid, ids,
                                                  vals, context=context)
        if not hasattr(ids, '__iter__'):
            ids = [ids]
        session = ConnectorSession(cr, uid, context=context)
        for record_id in ids:
            on_record_write.fire(self._name, session, record_id, vals.keys())
        return result

    def unlink(self, cr, uid, ids, context=None):
        result = super(inherit_class, self).unlink(cr, uid, ids, context=context)
        if not hasattr(ids, '__iter__'):
            ids = [ids]
        session = ConnectorSession(cr, uid, context=context)
        for record_id in ids:
            on_record_unlink.fire(self._name, session, record_id)
        return result

    inherit_class.create = create
    inherit_class.write = write
    inherit_class.unlink = unlink
    return inherit_class

res_partner = add_events('res.partner')
