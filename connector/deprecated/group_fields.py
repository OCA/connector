    # -*- encoding: utf-8 -*-
###############################################################################
#                                                                             #
#   base_external_referentials for OpenERP                                    #
#   Copyright (C) 2011 Akretion Sébastien BEAU <sebastien.beau@akretion.com>  #
#                                                                             #
#   This program is free software: you can redistribute it and/or modify      #
#   it under the terms of the GNU Affero General Public License as            #
#   published by the Free Software Foundation, either version 3 of the        #
#   License, or (at your option) any later version.                           #
#                                                                             #
#   This program is distributed in the hope that it will be useful,           #
#   but WITHOUT ANY WARRANTY; without even the implied warranty of            #
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the             #
#   GNU Affero General Public License for more details.                       #
#                                                                             #
#   You should have received a copy of the GNU Affero General Public License  #
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.     #
#                                                                             #
###############################################################################

from openerp.osv.orm import Model
from openerp.osv import fields
from openerp.osv.osv import except_osv
from openerp.tools.translate import _

class group_fields(Model):
    _name = 'group.fields'
    _description = 'trigger last write date by group of field'

    _columns = {
        'name': fields.char('Name', size=64, required=True),
        'column_name': fields.char('Column Name', size=64),
        'field_ids': fields.one2many('ir.model.fields', 'group_fields_id', 'Fields'),
        'model_id': fields.many2one('ir.model', 'Model'),
    }

    def create(self, cr, uid, vals, context=None):
        if not vals.get('column_name'):
            vals['column_name'] = 'x_trigger_%s' %vals['name'].lower().replace(' ', '_')
        field_obj = self.pool.get('ir.model.fields')

        #Create the generic date trigger
        if not field_obj.search(cr, uid, [('name', '=', 'x_last_update'), ('model_id', '=', vals['model_id'])], context=context):
            field_vals = {
                'name': 'x_trigger_update',
                'model_id': vals['model_id'],
#                'model': model_name,
                'field_description': 'trigger date field for %s'%(self._name),
                'ttype': 'datetime',
            }
            field_obj.create(cr, uid, field_vals, context=context)

        #Create specific date trigger
        if not field_obj.search(cr, uid, [('name', '=', vals['column_name']), ('model_id', '=', vals['model_id'])], context=context):
            field_vals = {
                'name': vals['column_name'],
                'model_id': vals['model_id'],
#                'model': model_name,
                'field_description': 'trigger date field for %s'%(vals['name']),
                'ttype': 'datetime',
            }
            field_obj.create(cr, uid, field_vals, context=context)
        return super(group_fields, self).create(cr, uid, vals, context=context)

    def write(self, cr, uid, ids, vals, context=None):
        if vals.get('column_name'):
            raise except_osv(_("User Error"), _("Changing Column name is not supported yet"))
        return super(group_fields, self).write(cr, uid, ids, vals, context=context)

class ir_model_fields(Model):
    _inherit = "ir.model.fields"

    _columns = {
        'group_fields_id': fields.many2one('group.fields', 'Trigger Group', domain="[('model_id', '=', model_id)]"),
    }

    def write(self, cr, uid, ids, vals, context=None):
        if vals.get('group_fields_id'):
            cr.execute("UPDATE ir_model_fields set group_fields_id = %s where id in %s", (vals['group_fields_id'], tuple(ids)))
            del vals['group_fields_id']
        if vals:
            return super(ir_model_fields, self).write(cr, uid, ids, vals, context=context)
        return True


