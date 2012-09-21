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

from openerp.osv.orm import Model
from openerp.osv import fields
from tempfile import TemporaryFile
from base_file_protocole.base_file_protocole import FileCsvWriter
from lxml import etree
from openerp.osv import orm


REF_FIELDS = ['location', 'apiusername', 'apipass']
#In your custom module you can specify which field will be visible
#example for making visible the fields location, apiusername and apipass
#for the referential type Magento :
#from base_external_referentials.external_referentials import REF_VISIBLE_FIELDS
#REF_VISIBLE_FIELDS['Magento'] = ['location', 'apiusername', 'apipass']

REF_VISIBLE_FIELDS = {}


class external_referential_category(Model):
    _name = 'external.referential.category'
    _description = 'External Referential Category (Ex: e-commerce, crm, warehouse)'

    _columns = {
        'name': fields.char('Name', size=64, required=True), #dont allow creation of type from frontend
        'type_ids': fields.one2many('external.referential.type', 'categ_id', 'Types', required=True)
    }

    def get_absolute_id(self, cr, uid, id, context=None):
        if isinstance(id,list):
            id = id[0]
        referential_categ = self.browse(cr, uid, id, context=context)
        categ_id = referential_categ.get_external_id(context=context)[referential_categ.id]
        if not categ_id:
            categ_id = referential_categ.name.replace('.','_').replace(' ','_')
        return categ_id

class external_referential_type(Model):
    _name = 'external.referential.type'
    _description = 'External Referential Type (Ex.Magento,Spree)'

    _columns = {
        'name': fields.char('Name', size=64, required=True), #dont allow creation of type from frontend
        'categ_id': fields.many2one('external.referential.category', 'Category', required=True),
        'version_ids': fields.one2many('external.referential.version', 'type_id', 'Versions', required=True),
        'code': fields.char('code', size=64, required=True),
    }

    def get_absolute_id(self, cr, uid, id, context=None):
        if isinstance(id,list):
            id = id[0]
        referential_type = self.browse(cr, uid, id, context=context)
        type_id = referential_type.get_external_id(context=context)[referential_type.id]
        if not type_id:
            type_id = referential_type.code.replace('.','_').replace(' ','_')
        return type_id


class external_referential_version(Model):
    _name = 'external.referential.version'
    _description = 'External Referential Version (Ex: v1.5.0.0 +, v1.3.2.4 +)'
    _rec_name = 'full_name'

    def get_absolute_id(self, cr, uid, id, context=None):
        if isinstance(id,list):
            id = id[0]
        version = self.browse(cr, uid, id, context=context)
        version_id = version.get_external_id(context=context)[version.id]
        if not version_id:
            version_id = version.code.replace('.','_').replace(' ','_')
        return version_id

    def _get_full_name(self, cr, uid, ids, name, arg, context=None):
        res = {}
        for version in self.read(cr, uid, ids, ['name', 'type_id'], context=context):
            res[version['id']] = '%s %s'%(version['type_id'][1], version['name'])
        return res

    _columns = {
        'full_name': fields.function(_get_full_name, store=True, type='char', size=64, string='Full Name'),
        'name': fields.char('name', size=64, required=True),
        'type_id': fields.many2one('external.referential.type', 'Type', required=True),
        'code': fields.char('code', size=64, required=True),
    }


class external_mapping_template(Model):
    _name = "external.mapping.template"
    _description = "The source mapping records"
    _rec_name = 'model'

    _columns = {
        'version_id':fields.many2one('external.referential.version', 'External Referential Version', ondelete='cascade'),
        'model_id': fields.many2one('ir.model', 'OpenERP Model', required=True, ondelete='cascade'),
        'model':fields.related('model_id', 'model', type='char', string='Model Name'),
        'external_list_method': fields.char('List Method', size=64),
        'external_search_method': fields.char('Search Method', size=64),
        'external_get_method': fields.char('Get Method', size=64),
        'external_update_method': fields.char('Update Method', size=64),
        'external_create_method': fields.char('Create Method', size=64),
        'external_delete_method': fields.char('Delete Method', size=64),
        'external_done_method': fields.char('Done Method', size=64),
        'key_for_external_id':fields.char('External field used as key', size=64),
        'external_resource_name':fields.char('External Resource Name', size=64),
        'extra_name': fields.char('Extra Name', size=100),
                }

class external_mappinglines_template(Model):
    _name = 'external.mappinglines.template'
    _description = 'The source mapping line records'
    _rec_name = 'name'

    def _name_get_fnc(self, cr, uid, ids, name, arg, context=None):
        res = {}
        for mapping_line in self.browse(cr, uid, ids, context):
            res[mapping_line.id] = mapping_line.evaluation_type == 'function' \
                                    and mapping_line.function_name \
                                    or mapping_line.external_field \
                                    or mapping_line.field_id.name
        return res

    _columns = {
        'name': fields.function(_name_get_fnc, type="char", string='Name'),
        'sequence': fields.integer('Sequence'),
        'version_id':fields.many2one('external.referential.version', 'External Referential Version', ondelete='cascade'),
        'field_id': fields.many2one('ir.model.fields', 'OpenERP Field', ondelete='cascade'),
        'mapping_id': fields.many2one('external.mapping.template', 'External Mapping', ondelete='cascade'),
        'external_field': fields.char('External Field', size=128),
        'type': fields.selection([('in_out', 'External <-> OpenERP'), ('in', 'External -> OpenERP'), ('out', 'External <- OpenERP')], 'Type'),
        'evaluation_type': fields.selection([('function', 'Function'), ('sub-mapping','Sub Mapping Line'), ('direct', 'Direct Mapping')], 'Evalution Type', required=True),
        'external_type': fields.selection([('url', 'URL'), ('datetime', 'Datetime'), ('unicode', 'String'), ('bool', 'Boolean'), ('int', 'Integer'), ('float', 'Float'), ('list', 'List'), ('dict', 'Dictionnary')], 'External Type', required=True),
        'datetime_format': fields.char('Datetime Format', size=32),
        'in_function': fields.text('Import in OpenERP Mapping Python Function'),
        'out_function': fields.text('Export from OpenERP Mapping Python Function'),
        'child_mapping_id': fields.many2one('external.mapping.template', 'Child Mapping', ondelete='cascade',
            help=('This give you the possibility to import data with a structure of Parent/child'
                'For example when you import a sale order, the sale order is the parent of the sale order line'
                'In this case you have to select the child mapping in order to convert the data'
                )
            ),
        'alternative_key': fields.boolean('Alternative Key', help=("Only one field can be selected as alternative key,"
                                                                "if no external id was found for the record the alternative key"
                                                                "will be used to identify the resource")),
        'function_name': fields.char('Function Name', size=128),
        }


class external_referential(Model):
    """External referential can have the option _lang_support. It can be equal to :
            - fields_with_main_lang : the fields to create will be organized all in the main lang and only the translatable fields in the others.example : {'main_lang': {trad_field : value, untrad_field: value, trad_field : value, untrad_field : value ...}, 'other_lang': {trad_field: value, trad_field: value}, ...}
            - fields_with_no_lang : all the fields untranslatable are grouped and the translatable fields are grouped in each lang. example : {'no_lang' : {untrad_field: value, untrad_field: value, untrad_field: value}, 'lang_one' : {trad_field: value, trad_field: value}, 'lang_two' : {trad_field: value, trad_field: value} ...}
            - all_fields : all the fields are in all languagues. example = {'lang_one' : {all_fields}, 'lang_two': {all_fields}...}"""
    _name = 'external.referential'
    _description = 'External Referential'

    _lang_support = 'fields_with_main_lang'

    #Only user that can write crypted field can read it
    _crypted_field = ['apiusername', 'apipass', 'location']


    def onchange_version_id(self, cr, uid, ids, version_id, context=None):
        version = self.pool.get('external.referential.version').browse(cr, uid, version_id, context=context)
        return {'value': {'type_name': version.type_id.name}}

    def read(self,cr, uid, ids, fields=None, context=None, load='_classic_read'):
        canwrite = self.check_write(cr, uid, raise_exception=False)
        res = super(external_referential, self).read(cr, uid, ids, fields=fields, context=context, load=load)
        if not canwrite:
            for val in res:
                for crypted_field in self._crypted_field:
                    if val.get(crypted_field):
                        val[crypted_field]='********'
        return res


    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        """
        Override the original field view get in order to insert dynamically the various fields need
        for the configuration of the referential
        """
        # use lxml to compose the arch XML
        result = super(external_referential, self).fields_view_get(cr, uid,
                                                                    view_id=view_id,
                                                                    view_type=view_type,
                                                                    context=context,
                                                                    toolbar=toolbar,
                                                                    submenu=submenu,
                                                                )
        if view_type == 'form':
            eview = etree.fromstring(result['arch'])
            toupdate_fields = []
            for field_name in REF_FIELDS:
                field = eview.xpath("//field[@name='%s']"%field_name)
                if field:
                    field = field[0]
                    referentials = []
                    for ref_type, visible_fields in REF_VISIBLE_FIELDS.items():
                        if field_name in visible_fields:
                            referentials.append(ref_type)
                    field.set('attrs', """{
                                    'invisible': [('type_name', 'not in', %s)],
                                    'required': [('type_name', 'in', %s)]
                                        }"""%(referentials, referentials))
                    orm.setup_modifiers(field, field=result['fields'][field_name], context=context)
                    result['arch'] = etree.tostring(eview, pretty_print=True)
        return result

    def external_connection(self, cr, uid, referential, debug=False, context=None):
        """Should be overridden to provide valid external referential connection"""
        return False

    def import_referentials(self, cr, uid, ids, context=None):
        self.import_resources(cr, uid, ids, 'external.referential', context=context)
        return True

    def _prepare_mapping_vals(self, cr, uid, referential_id, mapping_vals, context=None):
        return {
                    'referential_id': referential_id,
                    'template_id': mapping_vals['id'],
                    'model_id': mapping_vals['model_id'][0] or False,
                    'external_list_method': mapping_vals['external_list_method'],
                    'external_search_method': mapping_vals['external_search_method'],
                    'external_get_method': mapping_vals['external_get_method'],
                    'external_update_method': mapping_vals['external_update_method'],
                    'external_create_method': mapping_vals['external_create_method'],
                    'external_delete_method': mapping_vals['external_delete_method'],
                    'external_done_method': mapping_vals['external_done_method'],
                    'key_for_external_id': mapping_vals['key_for_external_id'],
                    'external_resource_name': mapping_vals['external_resource_name'],
                    'extra_name': mapping_vals['extra_name'],
                }

    def _prepare_mapping_line_vals(self, cr, uid, mapping_id, mapping_line_vals, context=None):
        return {
                    'sequence': mapping_line_vals['sequence'] or 0,
                    'external_field': mapping_line_vals['external_field'],
                    'template_id': mapping_line_vals['id'],
                    'mapping_id': mapping_id,
                    'type': mapping_line_vals['type'],
                    'evaluation_type': mapping_line_vals['evaluation_type'],
                    'external_type': mapping_line_vals['external_type'],
                    'datetime_format': mapping_line_vals['datetime_format'],
                    'in_function': mapping_line_vals['in_function'],
                    'out_function': mapping_line_vals['out_function'],
                    'field_id': mapping_line_vals['field_id'] and mapping_line_vals['field_id'][0] or False,
                    'alternative_key': mapping_line_vals['alternative_key'],
                    'function_name': mapping_line_vals['function_name'],
                        }

    def refresh_mapping(self, cr, uid, ids, context=None):
        #This function will reinstate mapping & mapping_lines for registered objects
        for id in ids:
            ext_ref = self.browse(cr, uid, id)
            mappings_obj = self.pool.get('external.mapping')
            mapping_line_obj = self.pool.get('external.mapping.line')
            mapping_tmpl_obj = self.pool.get('external.mapping.template')

            existing_mapping_line_ids = mapping_line_obj.search(cr, uid, [['mapping_id.referential_id', '=', id], ['template_id', '!=', False]], context=context)
            mapping_line_obj.unlink(cr, uid, existing_mapping_line_ids)

            link_parent_child_mapping = []
            template_mapping_id_to_mapping_id = {}
            #Fetch mapping lines now
            mapping_src_ids = self.pool.get('external.mapping.template').search(cr, uid, [('version_id', '=', ext_ref.version_id.id)])
            for each_mapping_rec in self.pool.get('external.mapping.template').read(cr, uid, mapping_src_ids, []):
                existing_ids = mappings_obj.search(cr, uid, [('referential_id', '=', id), ('template_id', '=', each_mapping_rec['id'])])
                vals = self._prepare_mapping_vals(cr, uid, id, each_mapping_rec, context=context)

                if len(existing_ids) == 0:
                    mapping_id = mappings_obj.create(cr, uid, vals)
                else:
                    mapping_id = existing_ids[0]
                    self.pool.get('external.mapping').write(cr, uid, mapping_id, vals, context=context)

                template_mapping_id_to_mapping_id[each_mapping_rec['id']] = mapping_id
                #Now create mapping lines of the created mapping model
                mapping_lines_src_ids = self.pool.get('external.mappinglines.template').search(cr, uid, [('mapping_id', '=', each_mapping_rec['id'])])
                for each_mapping_line_rec in  self.pool.get('external.mappinglines.template').read(cr, uid, mapping_lines_src_ids, []):
                    vals = self._prepare_mapping_line_vals(cr, uid, mapping_id, each_mapping_line_rec, context=context)
                    mapping_line_id = mapping_line_obj.create(cr, uid, vals)
                    if each_mapping_line_rec['child_mapping_id']:
                        link_parent_child_mapping.append([mapping_line_id, each_mapping_line_rec['child_mapping_id'][0]])

            #Now link the sub-mapping to the corresponding child
            for mapping_line_id, mapping_tmpl_id in link_parent_child_mapping:
                mapping_id = template_mapping_id_to_mapping_id[mapping_tmpl_id]
                mapping_line_obj.write(cr, uid, mapping_line_id, {'child_mapping_id': mapping_id}, context=context)
        return True


    _columns = {
        'name': fields.char('Name', size=32, required=True),
        'type_id': fields.related('version_id', 'type_id', type='many2one', relation='external.referential.type', string='External Type'),
        'type_name': fields.related('type_id', 'name', type='char', string='External Type Name',
                                    store=True),
        'categ_id': fields.related('type_id', 'categ_id', type='many2one', relation='external.referential.category', string='External Category'),
        'categ_name': fields.related('categ_id', 'name', type='char', string='External Category Name'),
        'version_id': fields.many2one('external.referential.version', 'Referential Version', required=True),
        'location': fields.char('Location', size=200),
        'apiusername': fields.char('User Name', size=64),
        'apipass': fields.char('Password', size=64),
        'mapping_ids': fields.one2many('external.mapping', 'referential_id', 'Mappings'),
        'create_date': fields.datetime('Creation Date', readonly=True, help="Date on which external referential is created."),
        'debug': fields.boolean('Debug', help='If debug mode is active all request between the external referential and OpenERP will be in the log')
    }

    _sql_constraints = [
        ('name_uniq', 'unique (name)', 'Referential names must be unique !')
    ]

    def _test_dot_in_name(self, cr, uid, ids, context=None):
        for referential in self.browse(cr, uid, ids):
            if '.' in referential.name:
                return False
        return True

    # Method to export external referential category
    def build_external_ref_categ(self, cr, uid, id, context=None):
        if isinstance(id,list):
            id = id[0]
        output_file = TemporaryFile('w+b')
        fieldnames = ['id', 'name']
        csv = FileCsvWriter(output_file, fieldnames, encoding="utf-8", writeheader=True, delimiter=',', quotechar='"')

        referential = self.browse(cr, uid, id, context=context)
        row = {
            'id': referential.type_id.categ_id.name,
            'name': referential.type_id.categ_id.name,
        }
        csv.writerow(row)
        return self.pool.get('pop.up.file').open_output_file(cr, uid, 'external.referential.category.csv', output_file, 'Referential category export', context=context)

    # Method to export external referential type
    def build_external_ref_type(self, cr, uid, id, context=None):
        if isinstance(id,list):
            id = id[0]
        output_file = TemporaryFile('w+b')
        fieldnames = ['id', 'name', 'categ_id:id', 'code']
        csv = FileCsvWriter(output_file, fieldnames, encoding="utf-8", writeheader=True, delimiter=',', quotechar='"')

        referential = self.browse(cr, uid, id, context=context)
        row = {
            'id': referential.type_id.get_absolute_id(context=context),
            'name': referential.type_id.name,
            'categ_id:id': referential.categ_id.get_absolute_id(context=context),
            'code': referential.type_id.code,
        }
        csv.writerow(row)
        return self.pool.get('pop.up.file').open_output_file(cr, uid, 'external.referential.type.csv', output_file, 'Referential Type Export', context=context)

    # Method to export external referential version
    def build_external_ref_version(self, cr, uid, id, context=None):
        if isinstance(id,list):
            id = id[0]
        output_file = TemporaryFile('w+b')
        fieldnames = ['id','name','type_id:id', 'code']
        csv = FileCsvWriter(output_file, fieldnames, encoding="utf-8", writeheader=True, delimiter=',', quotechar='"')

        referential = self.browse(cr, uid, id, context=context)
        row = {
            'id': referential.version_id.get_absolute_id(context=context),
            'name': referential.version_id.name,
            'type_id:id': referential.type_id.get_absolute_id(context=context),
            'code': referential.version_id.code,
        }
        csv.writerow(row)
        return self.pool.get('pop.up.file').open_output_file(cr, uid, 'external.referential.version.csv', output_file, 'Referential Version Export', context=context)

    def _prepare_external_referential_fieldnames(self, cr, uid, context=None):
        return ['id', 'name', 'version_id:id','location','apiusername','apipass','debug']

    def _prepare_external_referential_vals(self, cr, uid, referential, context=None):
        return {
            'id': referential.get_absolute_id(context=context),
            'name': referential.name,
            'version_id:id': referential.version_id.get_absolute_id(context=context),
            'location': referential.location,
            'apiusername': referential.apiusername,
            'apipass': referential.apipass,
            'debug': referential.debug,
        }

    # Method to export external referential
    def build_external_ref(self, cr, uid, id, context=None):
        if isinstance(id,list):
            id = id[0]
        output_file = TemporaryFile('w+b')
        fieldnames = self._prepare_external_referential_fieldnames(cr, uid, context=context)
        csv = FileCsvWriter(output_file, fieldnames, encoding="utf-8", writeheader=True, delimiter=',', quotechar='"')

        referential = self.browse(cr, uid, id, context=context)
        row = self._prepare_external_referential_vals(cr, uid, referential, context=context)
        csv.writerow(row)
        return self.pool.get('pop.up.file').open_output_file(cr, uid, 'external.referential.csv', output_file, 'Referential Type Export', context=context)

    def _prepare_mapping_fieldnames(self, cr, uid, context=None):
        return [
          'id',
          'version_id:id',
          'model_id:id',
          'extra_name',
          'external_resource_name',
          'key_for_external_id',
          'external_list_method',
          'external_search_method',
          'external_get_method',
          'external_update_method',
          'external_create_method',
          'external_delete_method',
          'external_done_method',
        ]

    def _prepare_mapping_template_vals(self, cr, uid, mapping, context=None):
        return {
                'id': mapping.get_absolute_id(context=context),
                'model_id:id': mapping.model_id.get_external_id(context=context)[mapping.model_id.id],
                'extra_name': mapping.extra_name or '',
                'external_list_method': mapping.external_list_method or '',
                'external_search_method': mapping.external_search_method or '',
                'external_get_method': mapping.external_get_method or '',
                'external_update_method': mapping.external_update_method or '',
                'external_create_method': mapping.external_create_method or '',
                'external_delete_method': mapping.external_delete_method or '',
                'external_done_method': mapping.external_done_method or '',
                'key_for_external_id': mapping.key_for_external_id or '',
                'external_resource_name': mapping.external_resource_name or '',
                'version_id:id': mapping.referential_id.version_id.get_absolute_id(context=context), # USEFULL ???
            }

    # Method to export external referential type
    def build_external_mapping_template(self, cr, uid, id, context=None):
        if isinstance(id,list):
            id = id[0]
        output_file = TemporaryFile('w+b')
        fieldnames = self._prepare_mapping_fieldnames(cr, uid, context=context)

        csv = FileCsvWriter(output_file, fieldnames, encoding="utf-8", writeheader=True, delimiter=',', quotechar='"')

        referential = self.browse(cr, uid, id, context=context)
        for mapping in referential.mapping_ids:
            row = self._prepare_mapping_template_vals(cr, uid, mapping, context=context)
            csv.writerow(row)
        return self.pool.get('pop.up.file').open_output_file(cr, uid, 'external.mapping.template.csv', output_file, 'Mapping Template Export', context=context)

    def _prepare_mappingline_fieldnames(self, cr, uid, context=None):
        return [
          'id',
          'mapping_id:id',
          'sequence',
          'type',
          'evaluation_type',
          'field_id:id',
          'external_field',
          'external_type',
          'datetime_format',
          'function_name',
          'in_function',
          'out_function',
          'child_mapping_id:id',
          'alternative_key',
        ]

    def _prepare_mappingline_template_vals(self, cr, uid, line, context=None):
        return {
                    'id': line.get_absolute_id(context=context),
                    'sequence': line.sequence or 0,
                    'type': line.type or '',
                    'evaluation_type': line.evaluation_type or '',
                    'external_field': line.external_field or '',
                    'field_id:id': line.field_id and line.field_id.get_external_id(context=context)[line.field_id.id],
                    'external_type': line.external_type or '',
                    'alternative_key': str(line.alternative_key) or '',
                    'mapping_id:id': line.mapping_id.get_absolute_id(context=context),
                    'function_name': line.function_name or '',
                    'in_function': line.in_function or '',
                    'out_function': line.out_function or '',
                    'child_mapping_id:id': line.child_mapping_id and line.child_mapping_id.get_absolute_id(context=context) or '',
                    'datetime_format': line.datetime_format or '',
                }

    # Method to export external referential type
    def build_external_mapping_lines(self, cr, uid, id, context=None):
        if isinstance(id,list):
            id = id[0]
        output_file = TemporaryFile('w+b')
        fieldnames = self._prepare_mappingline_fieldnames(cr, uid, context=context)

        csv = FileCsvWriter(output_file, fieldnames, encoding="utf-8", writeheader=True, delimiter=',', quotechar='"')

        referential = self.browse(cr, uid, id, context=context)
        for mapping in referential.mapping_ids:
            for line in mapping.mapping_ids:
                row = self._prepare_mappingline_template_vals(cr, uid, line, context=context)
                csv.writerow(row)
        return self.pool.get('pop.up.file').open_output_file(cr, uid, 'external.mappinglines.template.csv', output_file, 'Mapping Template Export', context=context)

    _constraints = [
        (_test_dot_in_name, 'The name cannot contain a dot!', ['name']),
    ]

    #TODO warning on name change if mapping exist: Implemented in attrs

    def get_absolute_id(self, cr, uid, id, context=None):
        if isinstance(id,list):
            id = id[0]
        referential = self.browse(cr, uid, id, context=context)
        referential_id = referential.get_external_id(context=context)[referential.id]
        if not referential_id:
            referential_id = referential.name.replace('.','_').replace(' ','_')
        return referential_id


class external_mapping_line(Model):
    _name = 'external.mapping.line'
    _description = 'Field Mapping'
    _rec_name = 'name'

    def _name_get_fnc(self, cr, uid, ids, name, arg, context=None):
        res = {}
        for mapping_line in self.browse(cr, uid, ids, context):
            res[mapping_line.id] = (mapping_line.evaluation_type == 'function' \
                                    and mapping_line.function_name \
                                    or mapping_line.external_field \
                                    or mapping_line.field_id.name) \
                                    + (mapping_line.mapping_id.extra_name \
                                    and ('=>' + mapping_line.mapping_id.extra_name) or '')
        return res

    _columns = {
        'name': fields.function(_name_get_fnc, type="char", string='Name', size=256),
    }


class external_mapping(Model):
    _name = 'external.mapping'
    _description = 'External Mapping'
    _rec_name = 'model'

    def _get_related_model_ids(self, cr, uid, ids, name, arg, context=None):
        "Used to retrieve model field one can map without ambiguity. Fields come from Inherited objects"
        res = {}
        for mapping in self.browse(cr, uid, ids, context): #FIXME: could be fully recursive instead of only 1 level
            main_model = mapping.model_id.model
            inherits_model = [x for x in self.pool.get(main_model)._inherits]
            model_ids = [mapping.model_id.id] + self.pool.get('ir.model').search(cr, uid, [['model','in', inherits_model]], context=context)
            res[mapping.id] = model_ids
        return res

    def _related_model_ids(self, cr, uid, model, context=None):
        inherits_model = [x for x in self.pool.get(model.model)._inherits]
        model_ids = [model.id] + self.pool.get('ir.model').search(cr, uid, [['model','in', inherits_model]], context=context)
        return model_ids

    def model_id_change(self, cr, uid, ids, model_id=None, context=None):
        if model_id:
            model = self.pool.get('ir.model').browse(cr, uid, model_id, context=context)
            return {'value': {'related_model_ids': self._related_model_ids(cr, uid, model, context=context)}}
        else:
            return {}

    def create(self, cr, uid, vals, context=None):
        res = super(external_mapping, self).create(cr, uid, vals, context)
        self.pool.get('ir.model').create_external_link(cr, uid, vals['model_id'], context=context)
        return res

    def write(self, cr, uid, ids, vals, context=None):
        res = super(external_mapping, self).write(cr, uid, ids, vals, context=context)
        if vals.get('model_id'):
            self.pool.get('ir.model').create_external_link(cr, uid, vals['model_id'], context=context)
        return res

    _columns = {
        'extra_name': fields.char('Extra Name', size=100, help="In case you need to make many mappings on the same object"),
        'template_id': fields.many2one('external.mapping.template', 'External Mapping Template'),
        'referential_id': fields.many2one('external.referential', 'External Referential', required=True, ondelete='cascade'),
        'model_id': fields.many2one('ir.model', 'OpenERP Model', required=True, ondelete='cascade'),
        'model':fields.related('model_id', 'model', type='char', string='Model Name'),
        'related_model_ids': fields.function(_get_related_model_ids, type="many2many", relation="ir.model", string='Related Inherited Models', help="potentially inherited through '_inherits' model, used for mapping field selection"),
        'external_list_method': fields.char('List Method', size=64),
        'external_search_method': fields.char('Search Method', size=64),
        'external_get_method': fields.char('Get Method', size=64),
        'external_update_method': fields.char('Update Method', size=64),
        'external_create_method': fields.char('Create Method', size=64),
        'external_delete_method': fields.char('Delete Method', size=64),
        'external_done_method': fields.char('Done Method', size=64),
        'mapping_ids': fields.one2many('external.mapping.line', 'mapping_id', 'Mappings Lines'),
        'key_for_external_id':fields.char('External field used as key', size=64),
        'external_resource_name':fields.char('External Resource Name', size=64),
    }

    # Method to set mapping with all object files
    def add_all_fields(self, cr, uid, ids, context=None):
        mapping_line_obj = self.pool.get('external.mapping.line')
        mapping = self.browse(cr, uid, ids)[0]
        for field in mapping.model_id.field_id:
            vals = {'mapping_id': mapping.id,
                    'field_id': field.id,
                    'type' : 'in_out',
                    }
            mapping_line_obj.create(cr, uid, vals)
        return True

    # Method to export the mapping file
    def create_mapping_file(self, cr, uid, id, context=None):
        if isinstance(id,list):
            id = id[0]
        output_file = TemporaryFile('w+b')
        fieldnames = self.pool.get('external.referential')._prepare_mappingline_fieldnames(cr, uid, context=context)
        csv = FileCsvWriter(output_file, fieldnames, encoding="utf-8", writeheader=True, delimiter=',', quotechar='"')

        mapping = self.browse(cr, uid, id, context=context)
        for line in mapping.mapping_ids:
            row =self.pool.get('external.referential')._prepare_mappingline_template_vals(cr, uid, line, context=context)
            csv.writerow(row)
        return self.pool.get('pop.up.file').open_output_file(cr, uid, 'external.mappinglines.template.csv', output_file, 'Mapping Line Export', context=context)

    def get_absolute_id(self, cr, uid, id, context=None):
        if isinstance(id,list):
            id = id[0]
        mapping = self.browse(cr, uid, id, context=context)
        if mapping.template_id:
            mapping_id = mapping.template_id.get_external_id(context=context)[mapping.template_id.id]
        else:
            version_code = mapping.referential_id.version_id.code.replace(' ','_')
            mapping_name = mapping.model + (mapping.extra_name and ('_' + mapping.extra_name) or '')
            mapping_id = (version_code + '_' + mapping_name).replace('.','_')
        return mapping_id

    def _get_related_child_mapping_ids(self, cr, uid, ids, context=None):
        res = []
        tmp_res = []
        for parent_mapping in self.browse(cr, uid, ids, context=context):
            for child in parent_mapping.mapping_ids:
                if child.evaluation_type == 'sub-mapping':
                    res.append(child.child_mapping_id.id)
                    tmp_res += (self._get_related_child_mapping_ids(cr, uid, [child.child_mapping_id.id], context=context))
        return res + tmp_res

    _sql_constraints = [
        ('ref_template_uniq', 'unique (referential_id, template_id)', 'A referential can not have various mapping imported from the same template')
    ]

    def copy(self, cr, uid, id, default=None, context=None):
        if default is None:
            default = {}

        default['template_id'] = False

        return super(external_mapping, self).copy(cr, uid, id, default=default, context=context)

class external_mapping_line(Model): # FIXME : tidy up this remnant of old OERP version
    _inherit = 'external.mapping.line'

    _columns = {
        'template_id': fields.many2one('external.mappinglines.template', 'External Mapping Lines Template'),
        'referential_id': fields.related('mapping_id', 'referential_id', type='many2one', relation='external.referential', string='Referential'),
        'field_id': fields.many2one('ir.model.fields', 'OpenERP Field', ondelete='cascade'),
        'internal_field': fields.related('field_id', 'name', type='char', relation='ir.model.field', string='Field name',readonly=True),
        'external_field': fields.char('External Field', size=128, help=("When importing flat csv file from file exchange,"
                                "you can leave this field empty, because this field doesn't exist in your csv file'")),
        'mapping_id': fields.many2one('external.mapping', 'External Mapping', ondelete='cascade'),
        'related_model_id': fields.related('mapping_id', 'model_id', type='many2one', relation='ir.model', string='Related Model'),
        'type': fields.selection([('in_out', 'External <-> OpenERP'), ('in', 'External -> OpenERP'), ('out', 'External <- OpenERP')], 'Type'),
        'external_type': fields.selection([('url', 'URL'),('datetime', 'Datetime'), ('unicode', 'String'), ('bool', 'Boolean'), ('int', 'Integer'), ('float', 'Float'), ('list', 'List'), ('dict', 'Dictionnary')], 'External Type', required=True),
        'datetime_format': fields.char('Datetime Format', size=32),
        'evaluation_type': fields.selection([('function', 'Function'), ('sub-mapping','Sub Mapping Line'), ('direct', 'Direct Mapping')], 'Evalution Type', required=True),
        'in_function': fields.text('Import in OpenERP Mapping Python Function'),
        'out_function': fields.text('Export from OpenERP Mapping Python Function'),
        'sequence': fields.integer('Sequence', required=True),
        'selected': fields.boolean('Selected', help="to select for mapping"),
        'child_mapping_id': fields.many2one('external.mapping', 'Child Mapping',
            help=('This give you the possibility to import data with a structure of Parent/child'
                'For example when you import a sale order, the sale order is the parent of the sale order line'
                'In this case you have to select the child mapping in order to convert the data'
                )
            ),
        'alternative_key': fields.boolean('Alternative Key', help=("Only one field can be selected as alternative key,"
                                                                "if no external id was found for the record the alternative key"
                                                                "will be used to identify the resource")),
        'internal_type': fields.related('field_id','ttype', type="char", relation='ir.model.field', string='Internal Type'),
        'function_name': fields.char('Function Name', size=128),
    }

    _defaults = {
         'type' : lambda * a: 'in_out',
         'external_type': lambda *a: 'unicode',
         'evaluation_type': lambda *a: 'direct',
    }

    def _check_mapping_line_name(self, cr, uid, ids):
        for mapping_line in self.browse(cr, uid, ids):
            if (not mapping_line.field_id) and (not mapping_line.external_field):
                return False
        return True


    _sql_constraints = [
        ('ref_template_uniq', 'unique (referential_id, template_id)', 'A referential can not have various mapping line imported from the same template mapping line')
    ]
    _order = 'sequence asc'
    #TODO add constraint: not both field_id and external_field null

    def get_absolute_id(self, cr, uid, id, context=None):
        if isinstance(id,list):
            id = id[0]
        line = self.browse(cr, uid, id, context=context)
        if line.template_id:
            line_id = line.template_id.get_external_id(context=context)[line.template_id.id]
        else:
            version_code = line.referential_id.version_id.code.replace(' ','_')
            mapping_name = line.mapping_id.model + (line.mapping_id.extra_name and ('_' + line.mapping_id.extra_name) or '')
            line_name = line.name
            line_id = (version_code + '_' + mapping_name + '_' + line_name).replace('.','_')
        return line_id

    def copy(self, cr, uid, id, default=None, context=None):
        if default is None:
            default = {}

        default['template_id'] = False

        return super(external_mapping_line, self).copy(cr, uid, id, default=default, context=context)


class ir_model_data(Model):
    _inherit = "ir.model.data"

    def init(self, cr):
      #FIXME: migration workaround: we changed the ir_model_data usage to make standard CSV import work again
      cr.execute("select name from external_referential;")
      referentials = cr.fetchall()
      for tuple in referentials:
          name = "extref." + tuple[0]
          cr.execute("update ir_model_data set name = replace(name, '_mag_order', '/mag_order') where module = %s;", (name,))
          cr.execute("update ir_model_data set name = regexp_replace(name, '_([1-9])', E'/\\\\1') where module = %s;", (name,))
          cr.execute("update ir_model_data set name = replace(name, '.', '_') where module = %s;", (name,))
          cr.execute("update ir_model_data set module = replace(module, '.','/') where module = %s;", (name,))
      return True

    def _get_referential_id(self, cr, uid, ids, name, arg, context=None):
        res = {}
        for model_data in self.browse(cr, uid, ids, context):
            s = model_data.module.split('/') #we assume a module name with a '/' means external referential
            if len(s) > 1:
                ref_ids = self.pool.get('external.referential').search(cr, uid, [['name', '=', s[1]]])
                if ref_ids:
                    res[model_data.id] = ref_ids[0]
                else:
                    res[model_data.id] = False
            else:
                res[model_data.id] = False
        return res

    _columns = {
        'referential_id': fields.function(_get_referential_id, type="many2one", relation='external.referential', string='Ext. Referential', store=True),
        #'referential_id':fields.many2one('external.referential', 'Ext. Referential'),
        #'create_date': fields.datetime('Created date', readonly=True), #TODO used?
        #'write_date': fields.datetime('Updated date', readonly=True), #TODO used?
    }

    _sql_constraints = [
        ('external_reference_uniq_per_object', 'unique(model, res_id, referential_id)', 'You cannot have on record with multiple external id for a sae referential'),
    ]

