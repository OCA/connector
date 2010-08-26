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
        'name': fields.char('Name', size=64, required=True, readonly=True), #dont allow creation of type from frontend
    }
    
external_referential_type()

class external_mapping_template(osv.osv):
    _name = "external.mapping.template"
    _description = "The source mapping records"
    _columns = {
        'type_id':fields.many2one('external.referential.type', 'External Referential Type', ondelete='cascade', select=True),
        'model_id': fields.many2one('ir.model', 'OpenERP Model', required=True, select=True, ondelete='cascade'),
        'model':fields.related('model_id', 'model', type='char', string='Model Name'),
        'external_list_method': fields.char('List Method', size=64),
        'external_get_method': fields.char('Get Method', size=64),
        'external_update_method': fields.char('Update Method', size=64),
        'external_create_method': fields.char('Create Method', size=64),
        'external_delete_method': fields.char('Delete Method', size=64),
        'external_key_name':fields.char('External field used as key', size=64)
                }
external_mapping_template()

class external_mappinglines_template(osv.osv):
    _name = 'external.mappinglines.template'
    _description = 'The source mapping line records'
    _columns = {
        'type_id':fields.many2one('external.referential.type', 'External Referential Type', ondelete='cascade', select=True),
        'model_id': fields.many2one('ir.model', 'OpenERP Model', select=True, ondelete='cascade'),
        'model':fields.related('model_id', 'model', type='char', string='Model Name'),
        'external_field': fields.char('External Field', size=32),
        'type': fields.selection([('in_out', 'External <-> OpenERP'), ('in', 'External -> OpenERP'), ('out', 'External <- OpenERP')], 'Type'),
        'external_type': fields.selection([('str', 'String'), ('bool', 'Boolean'), ('int', 'Integer'), ('float', 'Float')], 'External Type'),
        'in_function': fields.text('Import in OpenERP Mapping Python Function'),
        'out_function': fields.text('Export from OpenERP Mapping Python Function'),
                }
external_mappinglines_template()

class external_referential(osv.osv):
    _name = 'external.referential'
    _description = 'External Referential'

    def refresh_mapping(self, cr, uid, ids, ctx={}):
        #This function will reinstate mapping & mapping_lines for registered objects
        for id in ids:
            ext_ref = self.browse(cr, uid, id)
            mappings_obj = self.pool.get('external.mapping')
            mapping_line_obj = self.pool.get('external.mapping.line')
            #Delete Existing mappings if any
            cr.execute("""select id from (select distinct external_mapping_line.id, external_mapping.model_id
                            from (external_mapping_line join external_mapping on external_mapping.id = external_mapping_line.mapping_id)
                            join external_mappinglines_template on (external_mappinglines_template.external_field = external_mapping_line.external_field
                            and external_mappinglines_template.model_id = external_mapping.model_id)
                            where external_mapping.referential_id=%s order by external_mapping_line.id) as tmp;""", (id,))
            existing_mapping_ids = cr.fetchall()
            if existing_mapping_ids:
                mapping_line_obj.unlink(cr, uid, [tuple[0] for tuple in existing_mapping_ids])

            #Fetch mapping lines now
            mapping_src_ids = self.pool.get('external.mapping.template').search(cr, uid, [('type_id', '=', ext_ref.type_id.id)])
            for each_mapping_rec in self.pool.get('external.mapping.template').read(cr, uid, mapping_src_ids, []):
                existing_ids = mappings_obj.search(cr, uid, [('referential_id', '=', id), ('model_id', '=', each_mapping_rec['model_id'][0] or False)])
                if len(existing_ids) == 0:
                    vals = {
                                    'referential_id': id,
                                    'model_id': each_mapping_rec['model_id'][0] or False,
                                    'external_list_method': each_mapping_rec['external_list_method'],
                                    'external_get_method': each_mapping_rec['external_get_method'],
                                    'external_update_method': each_mapping_rec['external_update_method'],
                                    'external_create_method': each_mapping_rec['external_create_method'],
                                    'external_delete_method': each_mapping_rec['external_delete_method'],
                                    'external_key_name': each_mapping_rec['external_key_name'],
                                                }
                    mapping_id = mappings_obj.create(cr, uid, vals)
                else:
                    mapping_id = existing_ids[0]
                #Now create mapping lines of the created mapping model
                mapping_lines_src_ids = self.pool.get('external.mappinglines.template').search(cr, uid, [('type_id', '=', ext_ref.type_id.id), ('model_id', '=', each_mapping_rec['model_id'][0])])
                for each_mapping_line_rec in  self.pool.get('external.mappinglines.template').read(cr, uid, mapping_lines_src_ids, []):
                    vals = {
                        'external_field': each_mapping_line_rec['external_field'],
                        'mapping_id': mapping_id,
                        'type': each_mapping_line_rec['type'],
                        'external_type': each_mapping_line_rec['external_type'],
                        'in_function': each_mapping_line_rec['in_function'],
                        'out_function': each_mapping_line_rec['out_function'],
                        }
                    mapping_line_obj.create(cr, uid, vals)
        return True
            
                
    _columns = {
        'name': fields.char('Name', size=64, required=True),
        'type_id': fields.many2one('external.referential.type', 'Referential Type', select=True),
        'location': fields.char('Location', size=200),
        'apiusername': fields.char('User Name', size=64),
        'apipass': fields.char('Password', size=64),
        'mapping_ids': fields.one2many('external.mapping', 'referential_id', 'Mappings'),
    }
    
    _sql_constraints = [
        ('name_uniq', 'unique (name)', 'Referential names must be unique !')
    ]
    
    #TODO warning on name change if mapping exist: Implemented in attrs
    
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
        'model':fields.related('model_id', 'model', type='char', string='Model Name'),
        'related_model_ids': fields.function(_get_related_model_ids, method=True, type="one2many", relation="ir.model", string='Related Inherited Models', help="potentially inherited through '_inherits' model, used for mapping field selection"),
        'external_list_method': fields.char('List Method', size=64),
        'external_get_method': fields.char('Get Method', size=64),
        'external_update_method': fields.char('Update Method', size=64),
        'external_create_method': fields.char('Create Method', size=64),
        'external_delete_method': fields.char('Delete Method', size=64),
        'mapping_ids': fields.one2many('external.mapping.line', 'mapping_id', 'Mappings Lines'),
        'external_key_name':fields.char('External field used as key', size=64, required=True)
    }

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
         'type' : lambda * a: 'in_out',
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

class ir_model_data(osv.osv):
    _inherit = "ir.model.data"

    def _get_external_referential_id(self, cr, uid, ids, name, arg, context=None):
        res = {}
        for model_data in self.browse(cr, uid, ids, context):
            s = model_data.module.split('.') #we assume a module name with a '.' means external referential
            if len(s) > 1:
                res[model_data.id] = self.pool.get('external.referential').search(cr, uid, [['name', '=', s[1]]])[0]
            else:
                res[model_data.id] = False
        return res

    _columns = {
        'external_referential_id': fields.function(_get_external_referential_id, method=True, type="many2one", relation='external.referential', string='Ext. Referential', store=True),
        #'external_referential_id':fields.many2one('external.referential', 'Ext. Referential'),
        #'create_date': fields.datetime('Created date', readonly=True), #TODO used?
        #'write_date': fields.datetime('Updated date', readonly=True), #TODO used?
    }

ir_model_data()
