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

#class external_osv(osv.osv):
#    pass

#TODO convertion external id -> OpenERP object using Object mapping_column_name key!
#same as mage_to_oe mageerp_osv conversion method
    
#external_osv()

class external_referential_type(osv.osv):
    _name = 'external.referential.type'
    _description = 'External Referential Type'
    
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
        'location': fields.char('Location', size=64),
        'username': fields.char('User Name', size=64),
        'password': fields.char('Password', size=64),
        'mapping_ids': fields.one2many('external.mapping', 'referential_id', 'Mappings'),
        'mapping_column_name': fields.function(_mapping_column_name, method=True, type="char", string='Column Name', help='Column in OpenERP mapped tables for bookkeeping the external id'),
    }
    
    _sql_constraints = [
        ('name_uniq', 'unique (name)', 'Referential names must be unique !')
    ]
    
    #TODO warning on name change if mapping exist
    
    def core_sync(self, cr, uid, ids, ctx={}):
        osv.except_osv(_("Not Implemented"), _("Not Implemented in abstract base module!"))
    
external_referential()


class external_mapping_line(osv.osv):
    _name = 'external.mapping.line'
    _description = 'Field Mapping'
    _rec_name = 'field_id'
    
    def _name_get_fnc(self, cr, uid, ids, name, arg, context=None):
        res = {}
        for mapping_line in self.browse(cr, uid, ids, context):
            res[mapping_line.id] = mapping_line.field_id or mapping_line.external_field
        return res
    
    _columns = {
        'field_id': fields.many2one('ir.model.fields', 'OpenERP Field', select=True, ondelete='cascade'),
        'mapping_id': fields.many2one('external.mapping', 'External Mapping', select=True, ondelete='cascade'),
        'external_field': fields.char('External Field', size=32),
        'type': fields.selection([('in_out', 'External <-> OpenERP'), ('in', 'External -> OpenERP'), ('out', 'External <- OpenERP')], 'Type'),
        'external_type': fields.selection([('str', 'String'), ('bool', 'Boolean'), ('int', 'Integer'), ('float', 'Float')], 'External Type'),
        'in_function': fields.text('Import in OpenERP Mapping Python Function'),
        'out_function': fields.text('Export from OpenERP Mapping Python Function'),
        'name_function': fields.function(_name_get_fnc, method=True, type="char", string='Full Name'),
    }
    
    _default = {
         'type' : lambda *a: 'in_out',
    }
    
    def _check_mapping_line_name(self, cr, uid, ids):
        for mapping_line in self.browse(cr, uid, ids, context):
            if (not mapping_line.field_id) and (not mapping_line.external_field):
                return False
        return True
    
    _constraints = [
        (_check_mapping_line_name, "Error ! Invalid Mapping Line Name: Field and External Field cannot be both null", ['parent_id'])
    ]
    
    _order = 'type,external_type'
    #TODO add constraint: not both field_id and external_field null
external_mapping_line()


class external_mapping(osv.osv):
    _name = 'external.mapping'
    _description = 'External Mapping'
    _rec_name = 'model_id'
    _columns = {
        'referential_id': fields.many2one('external.referential', 'External Referential', required=True, select=True, ondelete='cascade'),
        'model_id': fields.many2one('ir.model', 'OpenERP Model', required=True, select=True, ondelete='cascade'),
        'external_list_method': fields.char('List Method', size=64),
        'external_get_method': fields.char('Get Method', size=64),
        'external_update_method': fields.char('Update Method', size=64),
        'external_create_method': fields.char('Create Method', size=64),
        'external_delete_method': fields.char('Delete Method', size=64),
        'mapping_ids': fields.one2many('external.mapping.line', 'mapping_id', 'Mappings Lines'),
    }
    
    def create(self):
                #Check if field already exists
        field_ids = self.pool.get('ir.model.fields').search(cr, uid, [('name', '=', field_name), ('model_id', '=', model_id)])
        if not field_ids:
            #The field is not there create it
            field_vals = {
                'name':field_name,
                'model_id':model_id,
                'model':'product.product',
                'field_description':vals.get('frontend_label', False) or vals['attribute_code'],
                'ttype':type_conversion[vals.get('frontend_input',False)],
                          }
            #IF char add size
            if field_vals['ttype'] == 'char':
                field_vals['size'] = 100
            if field_vals['ttype'] == 'many2one':
                field_vals['relation'] = 'magerp.product_attribute_options'
                field_vals['domain'] = "[('attribute_id','='," + str(crid) + ")]"
            field_vals['state'] = 'manual'
            #All field values are computed, now save
            field_id = self.pool.get('ir.model.fields').create(cr, uid, field_vals)
external_mapping()


class ir_model(osv.osv):
    _inherit = 'ir.model'
    _columns = {
        'external_list_method': fields.char('List Method', size=64),
        'external_get_method': fields.char('Get Method', size=64),
        'external_update_method': fields.char('Update Method', size=64),
        'external_create_method': fields.char('Create Method', size=64),
        'external_delete_method': fields.char('Delete Method', size=64),
        'external_mapping_ids': fields.one2many('external.mapping', 'model_id', 'External Mappings'),
    }
    
ir_model()
