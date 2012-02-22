# -*- encoding: utf-8 -*-
###############################################################################
#                                                                             #
#   file_exchange for OpenERP                                                 #
#   Copyright (C) 2012 Akretion Emmanuel Samyn <emmanuel.samyn@akretion.com>  #
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
from tools.safe_eval import safe_eval as eval
from osv import osv, fields
import netsvc
from base_external_referentials.external_osv import ExternalSession
import csv
from tempfile import TemporaryFile
from encodings.aliases import aliases
from tools.translate import _

class file_exchange(osv.osv):
    _name = "file.exchange"
    _description = "    file exchange"

    def get_default_fields_values(self, cr, uid, id, context=None):
        if isinstance(id, list):
            id = id[0]
        res = {}
        method = self.browse(cr, uid, id, context=context)
        for field in method.field_ids:
            if field.advanced_default_value:
                space = {'self': self,
                         'cr': cr,
                         'uid': uid,
                         'id': id,
                         'context': context,
                    }
                try:
                    exec field.advanced_default_value in space
                except Exception, e:
                    raise osv.except_osv(_('Error !'), _('Error when evaluating advanced default value: %s \n Exception: %s' %(fields.name,e)))
                res[field.name] = space.get('result', False)
            elif field.default_value:
                res[field.name] = field.default_value
        return res

    def _get_external_file_resources(self, cr, uid, external_session, filepath, filename, format, fields_name=None, context=None):
        external_file = external_session.connection.get(filepath, filename)
        if format == 'csv_no_header':
            res = csv.DictReader(external_file, fieldnames=fields_name, delimiter=';')
            return [x for x in res]
        return []

    def import_files(self, cr, uid, ids, context=None):
        for method_id in ids:
            res = self._import_files(cr, uid, method_id, context=context)
        return True

    def _import_files(self, cr, uid, method_id, context=None):
        file_fields_obj = self.pool.get('file.fields')
        method = self.browse(cr, uid, method_id, context=context)
        defaults = self.get_default_fields_values(cr, uid, method_id, context=context)
        external_session = ExternalSession(method.referential_id)
        mapping = {method.model_id.name : self._get_mapping(cr, uid, method.referential_id.id, context=context)}

        fields_name_ids = file_fields_obj.search(cr, uid, [['file_id', '=', method.id]], context=context)
        fields_name = [x['name'] for x in file_fields_obj.read(cr, uid, fields_name_ids, ['name'], context=context)]

        result = {"create_ids" : [], "write_ids" : []}
        list_filename = external_session.connection.search(method.folder_path, method.incomming_file)
        for filename in list_filename:
            external_session.logger.info("Start to import the file %s"%(filename,))
            resources = self._get_external_file_resources(cr, uid, external_session, method.folder_path, filename, method.format, fields_name, context=context)
            print 'res', resources
            import pdb; pdb.set_trace()
            res = self._record_external_resources(cr, uid, external_session, resources, defaults=defaults, mapping=mapping, context=context)
            external_session.logger.info("Finish to import the file %s"%(filename,))
        return result



    def export_files(self, cr, uid, ids, context=None):
        for method_id in ids:
            res = self._export_files(cr, uid, method_id, context=context)
        return True

    def _export_files(self, cr, uid, method_id, context=None):
    #TODO refactor this method toooooo long!!!!!
        def flat_resources(resources):
            result=[]
            for resource in resources:
                row_to_flat = False
                for key, value in resource.items():
                    if 'hidden_field_to_split_' in key:
                        if isinstance(value, list):
                            if row_to_flat:
                                raise osv.except_osv(_('Error !'), _('Can not flat two row in the same resource'))
                            row_to_flat = value
                        elif isinstance(value, dict):
                            for k,v in flat_resources([value])[0].items():
                                resource[k] = v
                        del resource[key]
                if row_to_flat:
                    for elements in row_to_flat:
                        tmp_dict = resource.copy()
                        tmp_dict.update(flat_resources([elements])[0])
                        result.append(tmp_dict)
                else:
                    result.append(resource)
            return result

        file_fields_obj = self.pool.get('file.fields')

        method = self.browse(cr, uid, method_id, context=context)
        external_session = ExternalSession(method.referential_id)
        external_session.logger.info("Start to export %s"%(method.name,))

        model_obj = self.pool.get(method.model_id.model)
        defaults = self.get_default_fields_values(cr, uid, method_id, context=context)
        encoding = method.encoding

        fields_name_ids = file_fields_obj.search(cr, uid, [['file_id', '=', method.id]], context=context)
        fields_info = file_fields_obj.read(cr, uid, fields_name_ids, ['name', 'mapping_line_id'], context=context)
        mapping_line_filter_ids = [x['mapping_line_id'][0] for x in fields_info if x['mapping_line_id']]
        fields_name = [x['name'] for x in fields_info]

        #TODO add a filter
        ids_to_export = model_obj.search(cr, uid, eval(method.search_filter), context=context)

        mapping = {model_obj._name : model_obj._get_mapping(cr, uid, external_session.referential_id.id, convertion_type='from_openerp_to_external', mapping_line_filter_ids=mapping_line_filter_ids, context=context)}
        fields_to_read = [x['internal_field'] for x in mapping[model_obj._name]['mapping_lines']]
        resources = model_obj._get_oe_resources_into_external_format(cr, uid, external_session, ids_to_export, mapping=mapping, mapping_line_filter_ids=mapping_line_filter_ids, fields=fields_to_read, defaults=defaults, context=context)
        if method.format == 'csv':
            output_file = TemporaryFile('w+b')
            fields_name = [x.encode(encoding) for x in fields_name]
            dw = csv.DictWriter(output_file, fieldnames=fields_name, delimiter=';', quotechar='"')
            dw.writeheader()
            resources = flat_resources(resources)
            for resource in resources:
                row = {}
                for k,v in resource.items():
                    try:
                        if isinstance(v, unicode):
                            row[k.encode(encoding)] = v.encode(encoding)
                        else:
                            row[k.encode(encoding)] = v
                    except:
                        row[k.encode(encoding)] = "ERROR"
                        #TODO raise an error correctly
                dw.writerow(row)
            output_file.seek(0)
        method.start_action_after_execution(model_obj, ids_to_export, context=context)
        filename = self.pool.get('ir.sequence')._process(method.filename)
        external_session.connection.send(method.folder_path, filename, output_file)
        external_session.logger.info("File transfert have been done succesfully %s"%(method.name,))
        return True

    def start_action_after_execution(self, cr, uid, id, self_object, object_ids, context=None):
        if isinstance(id, list):
            id = id[0]
        method = self.browse(cr, uid, id, context=context)
        if method.action_after_execution:
            space = {'self': self_object,
                     'cr': cr,
                     'uid': uid,
                     'ids': object_ids,
                     'context': context,
                }
            try:
                exec method.action_after_execution in space
            except Exception, e:
                raise osv.except_osv(_('Error !'), _('Error can not apply the python action default value: %s \n Exception: %s' %(method.name,e)))
        return True

    def _get_encoding(self, cr, user, context=None):
        result = [(x, x.replace('_', '-')) for x in set(aliases.values())]
        result.sort()
        return result

    _columns = {
        'name': fields.char('Name', size=64, help="Exchange description like the name of the supplier, bank,..."),
        'type': fields.selection([('in','IN'),('out','OUT'),], 'Type',help=("IN for files coming from the other system"
                                                                "and to be imported in the ERP ; OUT for files to be"
                                                                "generated from the ERP and send to the other system")),
        'model_id':fields.many2one('ir.model', 'Model',help="OpenEPR main object from which all the fields will be related"),
        'format' : fields.selection([('csv','CSV'),('csv_no_header','CSV WITHOUT HEADER')], 'File format'),
        'referential_id':fields.many2one('external.referential', 'Referential',help="Referential to use for connection and mapping"),
        'scheduler_id':fields.many2one('ir.cron', 'Scheduler',help="Scheduler that will execute the cron task"),
        'search_filter':  fields.char('Search Filter', size=256),
        'filename': fields.char('Filename', size=128, help="Filename will be used to generate the output file name or to read the incoming file"),
        'folder_path': fields.char('Folder Path', size=128, help="folder that containt the incomming or the outgoing file"),
        'encoding': fields.selection(_get_encoding, 'Encoding', require=True),
        'field_ids': fields.one2many('file.fields', 'file_id', 'Fields'),
        'action_after_execution': fields.text('Action After Execution', help="This python code will after the import or export will be done"),
    }

file_exchange()


class file_fields(osv.osv):
    _name = "file.fields"
    _description = "file fields"
    _order='sequence'

    def _clean_vals(self, vals):
        if vals.get('custom_name'):
            vals['mapping_line_id'] = False
        elif vals.get('mapping_line_id'):
            vals['custom_name'] = False
        return vals

    def create(self, cr, uid, vals, context=None):
        vals = self._clean_vals(vals)
        return super(file_fields, self).create(cr, uid, vals, context=context)

    def write(self, cr, uid, ids, vals, context=None):
        vals = self._clean_vals(vals)
        return super(file_fields, self).write(cr, uid, ids, vals, context=context)

    def _name_get_fnc(self, cr, uid, ids, name, arg, context=None):
        res = {}
        for file_field in self.browse(cr, uid, ids, context):
            res[file_field.id] = file_field.mapping_line_id and file_field.mapping_line_id.external_field or file_field.custom_name
        return res

    _columns = {
        #TODO the field name should be autocompleted bey the external field when selecting a mapping
        'name': fields.function(_name_get_fnc, type="char", string='Name', method=True),
        'custom_name': fields.char('Custom Name', size=64),
        'sequence': fields.integer('Sequence', required=True, help="The sequence field is used to define the order of the fields"),
        #TODO add a filter only fields that belong to the main object or to sub-object should be available
        'mapping_line_id': fields.many2one('external.mapping.line', 'OpenERP Mapping', domain = "[('referential_id', '=', parent.referential_id)]"),
        'file_id': fields.many2one('file.exchange', 'File Exchange', require="True"),
        'default_value': fields.char('Default Value', size=64),
        'advanced_default_value': fields.text('Advanced Default Value', help="This python code will be evaluate and the value in the varaible result will be used as defaut value"),
    }

file_fields()
