# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from osv import fields, osv
from sets import Set


class external_referential_type(osv.osv):
    _name = 'external.referential.type'
    _description = 'External Referential Type (Ex.Magento,Spree)'
    
    _columns = {
        'name': fields.char('Name', size=64, required=True),
    }
    
external_referential_type()

class external_referential(osv.osv):
    _name = 'external.referential'
    _description = 'External Referential'

    def _mapping_column_name(self, cr, uid, ids, name, arg, context=None):
        res = {}
        for referential in self.browse(cr, uid, ids, context):
            if referential.name:
                res[referential.id] = referential.name + "_id"
            else:
                res[referential.id] = False
        return res    
    
    _columns = {
        'name': fields.char('Name', size=64, required=True),
        'type_id': fields.many2one('external.referential.type', 'Referential Type', select=True),
        'location': fields.char('Location', size=200),
        'apiusername': fields.char('User Name', size=64),
        'apipass': fields.char('Password', size=64),
        'authentication': fields.text('Authentication Script'),
        'mapping_ids': fields.one2many('external.mapping', 'referential_id', 'Mappings'),
        'mapping_column_name': fields.function(_mapping_column_name, method=True, type="char", string='Column Name', help='Column in OpenERP mapped tables for bookkeeping the external id'),
        'state':fields.selection([
                                  ('draft','Drafting'),
                                  ('done','Done') 
                                  ],'Status',readonly=True,store=True)
    }
    
    _sql_constraints = [
        ('name_uniq', 'unique (name)', 'Referential names must be unique !')
    ]
    
    #TODO warning on name change if mapping exist: Implemented in attrs
    
    def core_sync(self, cr, uid, ids, ctx={}):
        osv.except_osv(_("Not Implemented"), _("Not Implemented in abstract base module!"))
    
external_referential()

class external_mapping_line(osv.osv):
    _name = 'external.mapping.line'
    _description = 'Field Mapping'
    _rec_name = 'name_function'
    
    def _name_get_fnc(self, cr, uid, ids, name, arg, context=None):
        res = {}
        for mapping_line in self.browse(cr, uid, ids, context):
            res[mapping_line.id] = mapping_line.field_id or mapping_line.external_field
        return res
    
    _columns = {
        'name_function': fields.function(_name_get_fnc, method=True, type="char", string='Full Name'),
    }

external_mapping_line()


class external_mapping(osv.osv):
    _name = 'external.mapping'
    _description = 'External Mapping'
    _rec_name = 'model_id'
    
    def _related_model_ids(self, cr, uid, model):
        field_ids = self.pool.get("ir.model.fields").search(cr, uid, [('model_id', '=', model.id), ('ttype', '=', 'many2one')])
        model_names = Set([model.model])
        for field in self.pool.get("ir.model.fields").browse(cr, uid, field_ids):
            model_names.add(field.relation)
        model_ids = self.pool.get("ir.model").search(cr, uid, [('model', 'in', [name for name in model_names])])
        return model_ids
    
    def _get_related_model_ids(self, cr, uid, ids, name, arg, context=None):
        "Used to retrieve model field one can map without ambiguity. Fields can come from Inherited objects or other many2one relations"
        res = {}
        for mapping in self.browse(cr, uid, ids, context): #FIXME: could be fully recursive instead of only 1 level
            res[mapping.id] = self._related_model_ids(cr, uid, mapping.model_id)
        return res
    
    def model_id_change(self, cr, uid, ids, model_id=None):
        if model_id:
            model = self.pool.get('ir.model').browse(cr, uid, model_id)
            return {'value': {'related_model_ids': self._related_model_ids(cr, uid, model)}}
        else:
            return {}
    
    _columns = {
        'referential_id': fields.many2one('external.referential', 'External Referential', required=True, select=True, ondelete='cascade'),
        'model_id': fields.many2one('ir.model', 'OpenERP Model', required=True, select=True, ondelete='cascade'),
        'model':fields.related('model_id','model',type='char', string='Model Name'),
        'related_model_ids': fields.function(_get_related_model_ids, method=True, type="one2many", relation="ir.model", string='Related Inherited Models', help="potentially inherited through '_inherits' model, used for mapping field selection"),
        'external_list_method': fields.char('List Method', size=64),
        'external_get_method': fields.char('Get Method', size=64),
        'external_update_method': fields.char('Update Method', size=64),
        'external_create_method': fields.char('Create Method', size=64),
        'external_delete_method': fields.char('Delete Method', size=64),
        'mapping_ids': fields.one2many('external.mapping.line', 'mapping_id', 'Mappings Lines'),
        'external_field_id':fields.many2one('ir.model.fields', 'Foreign Key Field'),
        'external_field':fields.related('external_field_id','name',type='char', string='Field Name'),
    }
    
    def create(self, cr, ui, vals, context=None):
        "check if external mapping key already exists, else create it"
        if not vals.get('external_field_id', False):
            referential = self.pool.get('external.referential').browse(cr, ui, vals['referential_id'])
            field_vals = {
                'name':referential.mapping_column_name,
                'model_id':vals['model_id'],
                'model':self.pool.get('ir.model').browse(cr, ui, vals['model_id']).model,
                'field_description':str(referential.mapping_column_name) + " Ref",
                'ttype':'integer',
            }
            field_id = self.pool.get('ir.model.fields').create(cr, ui, field_vals)
            vals['external_field_id'] = field_id
        return super(external_mapping, self).create(cr, ui, vals, context)

external_mapping()


class external_mapping_line(osv.osv):
    _inherit = 'external.mapping.line'
    
    _columns = {
        'field_id': fields.many2one('ir.model.fields', 'OpenERP Field', select=True, ondelete='cascade'),
        'external_field': fields.char('External Field', size=32),
        'mapping_id': fields.many2one('external.mapping', 'External Mapping', select=True, ondelete='cascade'),
        'related_model_id': fields.related('mapping_id', 'model_id', type='many2one', relation='ir.model', string='Related Model'),
        'type': fields.selection([('in_out', 'External <-> OpenERP'), ('in', 'External -> OpenERP'), ('out', 'External <- OpenERP')], 'Type'),
        'external_type': fields.selection([('str', 'String'), ('bool', 'Boolean'), ('int', 'Integer'), ('float', 'Float')], 'External Type'),
        'in_function': fields.text('Import in OpenERP Mapping Python Function'),
        'out_function': fields.text('Export from OpenERP Mapping Python Function'),
    }
    
    _default = {
         'type' : lambda *a: 'in_out',
    }
    
    def _check_mapping_line_name(self, cr, uid, ids):
        for mapping_line in self.browse(cr, uid, ids):
            if (not mapping_line.field_id) and (not mapping_line.external_field):
                return False
        return True
    
    _constraints = [
        (_check_mapping_line_name, "Error ! Invalid Mapping Line Name: Field and External Field cannot be both null", ['parent_id'])
    ]
    
    _order = 'type,external_type'
    #TODO add constraint: not both field_id and external_field null
external_mapping_line()
