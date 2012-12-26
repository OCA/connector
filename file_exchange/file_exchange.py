# -*- encoding: utf-8 -*-
###############################################################################
#                                                                             #
#   file_exchange for OpenERP                                                 #
#   Copyright (C) 2012 Akretion Emmanuel Samyn <emmanuel.samyn@akretion.com>  #
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
from tools.safe_eval import safe_eval
from openerp.osv.orm import Model
from openerp.osv import fields
from openerp.osv.osv import except_osv
from base_external_referentials.external_osv import ExternalSession
from base_file_protocole.base_file_protocole import FileCsvReader, FileCsvWriter, FileXlsReader
from base_external_referentials.decorator import open_report
from tempfile import TemporaryFile
from encodings.aliases import aliases
from tools.translate import _
from openerp.tools.config import config


#TODO implement the FileCsvWriter in base_file_protocole and remove import csv
import csv

class FileExchangeCsvReader(FileCsvReader):
    def __init__(self, f, pre_processing=None, **kwds):
        super(FileExchangeCsvReader, self).__init__(f, **kwds)
        self.pre_processing = pre_processing

    def next(self):
        row = super(FileExchangeCsvReader, self).next()
        if self.pre_processing:
            space = {'row': row,
                }
            try:
                exec self.pre_processing in space
            except Exception, e:
                raise except_osv(_('Error!'), _('Error can not apply the python action pre-processing value'))
        return row

class file_exchange(Model):
    _name = "file.exchange"
    _description = "file exchange"

    def get_export_default_fields_values(self, cr, uid, id, context=None):
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
                    raise except_osv(_('Error!'),
                                     _('Error when evaluating advanced default value: %s \n Exception: %s') % (fields.name,e))
                res[field.name] = space.get('result', False)
            elif field.default_value:
                res[field.name] = field.default_value
        return res

    def _get_external_file_resources(self, cr, uid, external_session, filepath, filename, format,
                    fields_name=None, mapping=None, mapping_id=None, external_file=None, context=None):
        if not external_file:
            external_file = external_session.connection.get(filepath, filename)
        method = external_session.sync_from_object
        model_obj = self.pool.get(method.mapping_id.model_id.model)
        if format in ['csv_no_header','csv']:
            merge_key_id = self.pool.get('file.fields').search(cr, uid, [
                                ('merge_key', '=', True),
                                ('mapping_line_id.related_model_id', '=', method.mapping_id.model_id.id),
                                ('file_id', '=', method.id)
                            ], context=context)
            merge_key = None
            if merge_key_id:
                merge_key = self.pool.get('file.fields').read(cr, uid, merge_key_id[0], ['name'], context=context)['name']
            mapping,mapping_id = model_obj._init_mapping(cr, uid, external_session.referential_id.id,
                                                        convertion_type='from_external_to_openerp',
                                                        mapping_id=method.mapping_id.id,
                                                        context=context)
            mapping_tree, merge_keys = self._get_mapping_tree(cr, uid, mapping_id, context=context)
            csv = FileExchangeCsvReader(external_file,
                                        fieldnames= format=='csv_no_header' and fields_name or None,
                                        delimiter=method.delimiter.encode('utf-8'),
                                        encoding=method.encoding,
                                        pre_processing=method.pre_processing)
            res = csv.reorganize(field_structure=mapping_tree, merge_keys=merge_keys, ref_field=merge_key)
        elif format in ['xls']:
            res = FileXlsReader(external_file.read()).read()
        return res

    def _get_mapping_tree(self, cr, uid, mapping_id, parent_name=None, grand_parent_name=None, context=None):
        mapping_tree = []
        result = []
        merge_keys = []
        mapping = self.pool.get('external.mapping').browse(cr, uid, mapping_id, context=context)
        mapping_name = "%s_%s" %(mapping.model_id.model, mapping.id)
        for mapping_line in mapping.mapping_ids:
            if mapping_line.evaluation_type == 'sub-mapping':
                res, sub_merge_keys = self._get_mapping_tree(cr, uid, mapping_line.child_mapping_id.id, mapping_name,  context=context)
                result = res + result
                merge_keys = merge_keys + sub_merge_keys
                if mapping_line.internal_type in ['one2many','many2many']:
                    merge_keys.append("%s_%s" %(mapping_line.child_mapping_id.model, mapping_line.child_mapping_id.id))
            else:
                if parent_name:
                    result.append((mapping_line.external_field , mapping_name))
        if grand_parent_name:
            result.append((mapping_name , parent_name))
        if not parent_name:
            result = list(set(result))
        return result, merge_keys

    #needed for cron task
    def start_task(self, cr, uid, ids, context=None):
        if context is None:
            context={}
        for method in self.browse(cr, uid, ids, context=context):
            if method.type == 'in':
                self.import_task(cr, uid, method.id, context=context)
            elif method.type == 'out':
                self.export_task(cr, uid, method.id, context=context)

    def import_task(self, cr, uid, method_id, context=None):
        if hasattr(method_id, '__iter__'):
            method_id = method_id[0]
        method = self.browse(cr, uid, method_id, context=context)
        if method.synchronize_from == 'pop_up':
            return self.import_file_form_pop_up(cr, uid, method.id, context=context)
        else:
            self._import_files(cr, uid, method.id, context=context)
            return True

    def export_task(self, cr, uid, method_id, context=None):
        if hasattr(method_id, '__iter__'):
            method_id = method_id[0]
        method = self.browse(cr, uid, method_id, context=context)
        return self._export_files(cr, uid, method.id, context=context)


    def import_file_form_pop_up(self, cr, uid, method_id, context=None):
        return self.pool.get('pop.up.file').open_input_file(cr, uid, 'import file', self._import_file_from_pop_up, [method_id], context=context)

    def _import_file_from_pop_up(self, cr, uid, method_id, input_file, input_filename, context=None):
        #TODO remove this duplicated code from import_file
        context['pop_up_callback'] = False
        context['file_exchange_id'] = method_id
        method = self.browse(cr, uid, method_id, context=context)
        external_session = ExternalSession(method.referential_id, method)
        file_fields_obj = self.pool.get('file.fields')
        model_obj = self.pool.get(method.mapping_id.model_id.model)
        mapping,mapping_id = model_obj._init_mapping(cr, uid, external_session.referential_id.id,
                                                        convertion_type='from_external_to_openerp',
                                                        mapping_id=method.mapping_id.id,
                                                        context=context)
        defaults = self._get_default_import_values(cr, uid, external_session, mapping_id, context=context)
        fields_name_ids = file_fields_obj.search(cr, uid, [['file_id', '=', method.id]], context=context)
        fields_name = [x['name'] for x in file_fields_obj.read(cr, uid, fields_name_ids, ['name'], context=context)]
        self._import_one_file(cr, uid, external_session, method_id, input_filename, defaults, mapping,
                                            mapping_id, fields_name, external_file=input_file, context=context)
        return True

    def _import_files(self, cr, uid, method_id, context=None):
        if context is None:
            context={}
        context['file_exchange_id'] = method_id
        file_fields_obj = self.pool.get('file.fields')
        method = self.browse(cr, uid, method_id, context=context)
        context['report_line_based_on'] = method.mapping_id.model_id.model
        external_session = ExternalSession(method.referential_id, method)
        model_obj = self.pool.get(method.mapping_id.model_id.model)
        mapping,mapping_id = model_obj._init_mapping(cr, uid, external_session.referential_id.id,
                                                        convertion_type='from_external_to_openerp',
                                                        mapping_id=method.mapping_id.id,
                                                        context=context)

        defaults = self._get_default_import_values(cr, uid, external_session, mapping_id, context=context)
        fields_name_ids = file_fields_obj.search(cr, uid, [['file_id', '=', method.id]], context=context)
        fields_name = [x['name'] for x in file_fields_obj.read(cr, uid, fields_name_ids, ['name'], context=context)]

        result = {"create_ids" : [], "write_ids" : []}
        list_filename = external_session.connection.search(method.folder_path, method.filename)
        if not list_filename:
            external_session.logger.info("No file '%s' found on the server"%(method.filename,))
        for filename in list_filename:
            res = self._import_one_file(cr, uid, external_session, method_id, filename, defaults,
                                                    mapping, mapping_id, fields_name, context=context)
            result["create_ids"] += res.get('create_ids',[])
            result["write_ids"] += res.get('write_ids',[])
        return result

    @open_report
    def _import_one_file(self, cr, uid, external_session, method_id, filename, defaults, mapping,
                                            mapping_id, fields_name, external_file=None, context=None):
        ids_imported = []
        method = self.browse(cr, uid, method_id, context=context)
        model_obj = self.pool.get(method.mapping_id.model_id.model)
        external_session.logger.info("Start to import the file %s"%(filename,))
        method.start_action('action_before_all', model_obj, context=context)
        resources = self._get_external_file_resources(cr, uid, external_session, method.folder_path,
                                                        filename, method.format, fields_name,
                                                        mapping=mapping,
                                                        mapping_id=mapping_id,
                                                        external_file=external_file,
                                                        context=context)
        res = self.pool.get(method.mapping_id.model_id.model)._record_external_resources(cr, uid,
                                                                        external_session, resources,
                                                                        defaults=defaults,
                                                                        mapping=mapping,
                                                                        mapping_id=mapping_id,
                                                                        context=context)
        ids_imported += res['create_ids'] + res['write_ids']
        method.start_action('action_after_all', model_obj, ids_imported, context=context)
        if method.synchronize_from == 'referential' and method.archive_folder_path:
            external_session.connection.move(method.folder_path, method.archive_folder_path, filename)
        external_session.logger.info("Finish to import the file %s"%(filename,))
        return res

    def _check_if_file_exist(self, cr, uid, external_session, folder_path, filename, context=None):
        exist = external_session.connection.search(folder_path, filename)
        if exist:
            raise except_osv(_('Error!'), _('The file "%s" already exist in the folder "%s"' %(filename, folder_path)))
        return False

    def _export_files(self, cr, uid, method_id, context=None):
    #TODO refactor this method toooooo long!!!!!
        def flat_resources(resources):
            result=[]
            for resource in resources:
                row_to_flat = False
                for key, value in resource.items():
                    if key != False:
                        if 'hidden_field_to_split_' in key:
                            if isinstance(value, list):
                                if row_to_flat:
                                    raise except_osv(_('Error!'), _('Can not flat two row in the same resource'))
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

    #=== Get connection
        external_session = ExternalSession(method.referential_id, method)
        sequence_obj = self.pool.get('ir.sequence')
        d = sequence_obj._interpolation_dict()
        filename = sequence_obj._interpolate(method.filename, d)
    #=== Check if file already exist in specified folder. If so, raise an alert
        if method.synchronize_from != 'pop_up':
            self._check_if_file_exist(cr, uid, external_session, method.folder_path, filename, context=context)
    #=== Start export
        external_session.logger.info("Start to export %s"%(method.name,))
        model_obj = self.pool.get(method.mapping_id.model_id.model)
        method.start_action('action_before_all', model_obj, context=context)
        defaults = self.get_export_default_fields_values(cr, uid, method_id, context=context)
        encoding = method.encoding

    #=== Get external file ids and fields
        fields_name_ids = file_fields_obj.search(cr, uid, [['file_id', '=', method.id]], context=context)
        fields_info = file_fields_obj.read(cr, uid, fields_name_ids, ['name', 'mapping_line_id'], context=context)
    #=== Get lines that need to be mapped
        mapping_line_filter_ids = [x['mapping_line_id'][0] for x in fields_info if x['mapping_line_id']]
        fields_name = [x['name'] for x in fields_info]
    #=== Apply filter
        #TODO add a filter
        ids_filter = "()" # In case not filter is filed in the form
        if method.search_filter != False:
            ids_filter = method.search_filter
        ids_to_export = model_obj.search(cr, uid, safe_eval(ids_filter, {'context': context}), context=context)
    #=== Start mapping
        mapping,mapping_id = model_obj._init_mapping(cr, uid, external_session.referential_id.id,
                                                    convertion_type='from_openerp_to_external',
                                                    mapping_line_filter_ids=mapping_line_filter_ids,
                                                    mapping_id=method.mapping_id.id,
                                                    context=context)
        fields_to_read = [x['internal_field'] for x in mapping[mapping_id]['mapping_lines']]
        # TODO : CASE fields_to_read is False !!!
        resources = model_obj._get_oe_resources_into_external_format(cr, uid, external_session,
                                                    ids_to_export,
                                                    mapping=mapping,mapping_id=mapping_id,
                                                    mapping_line_filter_ids=mapping_line_filter_ids,
                                                    fields=fields_to_read,
                                                    defaults=defaults,
                                                    context=context)
    #=== Check if content to export
        if not resources:
            external_session.logger.info("Not data to export for %s"%(method.name,))
            return True
        output_file =TemporaryFile('w+b')
        fields_name = [x.encode(encoding) for x in fields_name]
        dw = csv.DictWriter(output_file, fieldnames=fields_name, delimiter=';', quotechar='"')
#       dw.writeheader() TODO : only for python >= 2.7
        row = {}
    #=== Write CSV file
        if method.format == 'csv':
        #=== Write header
            for name in fields_name:
                row[name.encode(encoding)] = name.encode(encoding)
            dw.writerow(row)
        #=== Write content
        resources = flat_resources(resources)
        for resource in resources:
            row = {}
            for k,v in resource.items():
                if k!=False:
                    try:
                        if isinstance(v, unicode) and v!=False:
                            row[k.encode(encoding)] = v.encode(encoding)
                        else:
                            row[k.encode(encoding)] = v
                    except:
                        row[k.encode(encoding)] = "ERROR"
                    #TODO raise an error correctly
            dw.writerow(row)

        output_file.seek(0)
        method.start_action('action_after_all', model_obj, ids_to_export, context=context,external_session=external_session)
        output = self._send_output(cr, uid, external_session, method, filename, output_file, context=context)

        #Start linked task
        if method.linked_task:
            context['parent_ids'] = ids_to_export
            method.linked_task.start_task(context=context)

        return output

    def _send_output(self, cr, uid, external_session, method, filename, output_file, context=None):
        if method.synchronize_from == 'pop_up':
            return self.pool.get('pop.up.file').open_output_file(cr, uid, filename, output_file, 'File export', context=context)
        else:
            external_session.connection.send(method.folder_path, filename, output_file)
            external_session.logger.info("File transfert have been done succesfully %s"%(method.name,))
        return True

    def start_action(self, cr, uid, id, action_name, self_object, object_ids=None, resource=None,
                                                                context=None,external_session=None):
        if context is None:
            context={}
        if isinstance(id, list):
            id = id[0]
        method = self.browse(cr, uid, id, context=context)
        action_code = getattr(method, action_name)
        if action_code:
            space = {'self': self_object,
                     'cr': cr,
                     'uid': uid,
                     'ids': object_ids,
                     'resource': resource,
                     'context': context,
                     'external_session':external_session,
                }
            try:
                exec action_code in space
            except Exception, e:
                if config['debug_mode']: raise
                raise except_osv(_('Error!'),
                                 _("Error can not apply the python action '%s'"
                                   " for the method: '%s' \n Exception: '%s'") % (action_name, method.name,e))
            if 'result' in space:
                return space['result']
        return True

    def _get_encoding(self, cr, user, context=None):
        result = [(x, x.replace('_', '-')) for x in set(aliases.values())]
        result.sort()
        return result

    def _get_related_mapping_ids(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for parent in self.browse(cr, uid, ids, context=context):
            if parent.mapping_id:
                res[parent.id] =  [parent.mapping_id.id] + parent.mapping_id._get_related_child_mapping_ids()
            else:
                res[parent.id] = []
        return res

    _columns = {
        'name': fields.char('Name', size=64, help="Exchange description like the name of the supplier, bank,...", require=True),
        'type': fields.selection([('in','IN'),('out','OUT'),('in-out', 'IN & OUT')], 'Type',help=("IN for files coming from the other system"
                                                                "and to be imported in the ERP ; OUT for files to be"
                                                                "generated from the ERP and send to the other system")),
        'mapping_id':fields.many2one('external.mapping', 'External Mapping', require="True", domain="[('referential_id', '=', referential_id)]"),
        'format' : fields.selection([('csv','CSV'),('csv_no_header','CSV WITHOUT HEADER'), ('xls', 'XLS')], 'File format'),
        'referential_id':fields.many2one('external.referential', 'Referential',help="Referential to use for connection and mapping", require=True),
        'scheduler':fields.many2one('ir.cron', 'Scheduler',help="Scheduler that will execute the cron task"),
        'search_filter':  fields.char('Search Filter', size=256),
        'filename': fields.char('Filename', size=128, help="Filename will be used to generate the output file name or to read the incoming file. It is possible to use variables (check in sequence for syntax)", require=True),
        'folder_path': fields.char('Folder Path', size=128, help="folder that containt the incomming or the outgoing file"),
        'archive_folder_path': fields.char('Archive Folder Path', size=128, help="if a path is set when a file is imported the file will be automatically moved to this folder"),
        'encoding': fields.selection(_get_encoding, 'Encoding', require=True),
        'field_ids': fields.one2many('file.fields', 'file_id', 'Fields'),
        'action_before_all': fields.text('Action Before All', help="This python code will executed after the import/export"),
        'action_after_all': fields.text('Action After All', help="This python code will executed after the import/export"),
        'action_before_each': fields.text('Action Before Each', help="This python code will executed after each element of the import/export"),
        'action_after_each': fields.text('Action After Each', help="This python code will executed after each element of the import/export"),
        'check_if_import': fields.text('Check If Import', help="This python code will be executed before each element of the import"),
        'delimiter':fields.char('Fields delimiter', size=64, help="Delimiter used in the CSV file"),
        'lang': fields.many2one('res.lang', 'Language'),
        'import_default_fields':fields.one2many('file.default.import.values', 'file_id', 'Default Field'),
        'do_not_update':fields.boolean('Do Not Update'),
        'pre_processing': fields.text('Pre-Processing', help="This python code will be executed before merge of elements of the import"),
        'mapping_template_id':fields.many2one('external.mapping.template', 'External Mapping Template', require="True"),
        'notes': fields.text('Notes'),
        'related_mapping_ids': fields.function(_get_related_mapping_ids, type="many2many", relation="external.mapping", string='Related Mappings'),
        'synchronize_from': fields.selection([('referential', 'Referential'), ('pop_up', 'Pop Up')], string='Synchronize From'),
        'linked_task': fields.many2one('file.exchange', 'Linked Task'),
    }

    def get_absolute_id(self, cr, uid, id, context=None):
        if isinstance(id,list):
            id = id[0]
        file_exchange = self.browse(cr, uid, id, context=context)
        file_exchange_id = file_exchange.get_external_id(context=context)[file_exchange.id]
        if not file_exchange_id:
            file_exchange_id = file_exchange.name.replace(' ','_').replace('.','_')
        return file_exchange_id

    # Method to export the exchange file
    def create_exchange_file(self, cr, uid, id, context=None):
        if isinstance(id,list):
            id = id[0]
        output_file = TemporaryFile('w+b')
        fieldnames = ['id', 'name','referential_id:id', 'type','do_not_update', 'mapping_template_id:id', 'encoding', 'format', 'search_filter','delimiter', 'folder_path', 'archive_folder_path', 'filename', 'action_before_all', 'action_after_all', 'action_before_each', 'action_after_each', 'check_if_import', 'pre_processing']
        csv = FileCsvWriter(output_file, fieldnames, encoding="utf-8", writeheader=True, delimiter=',', quotechar='"')
        current_file = self.browse(cr, uid, id, context=context)
        row = {
            'id': current_file.get_absolute_id(context=context),
            'name': current_file.name,
            'referential_id:id':current_file.referential_id.get_absolute_id(context=context),
            'type': current_file.type,
            'do_not_update': str(current_file.do_not_update),
            'mapping_template_id:id': current_file.mapping_id.get_absolute_id(context=context),
            'encoding': current_file.encoding,
            'format': current_file.format,
            'search_filter': current_file.search_filter or '',
#            'lang'
            'delimiter': current_file.delimiter,
            'folder_path': current_file.folder_path or '',
            'archive_folder_path': current_file.archive_folder_path or '',
            'filename': current_file.filename,
            'action_before_all': current_file.action_before_all or '',
            'action_after_all': current_file.action_after_all or '',
            'action_before_each': current_file.action_before_each or '',
            'action_after_each': current_file.action_after_each or '',
            'check_if_import': current_file.check_if_import or '',
            'pre_processing': current_file.pre_processing or '',
        }
        csv.writerow(row)
        return self.pool.get('pop.up.file').open_output_file(cr, uid, 'file.exchange.csv', output_file, 'File Exchange Export', context=context)

    # Method to export the mapping file
    def create_file_fields(self, cr, uid, id, context=None):
        if isinstance(id,list):
            id = id[0]
        output_file = TemporaryFile('w+b')
        fieldnames = ['id', 'is_required', 'name', 'custom_name', 'sequence', 'mappinglines_template_id:id', 'file_id:id', 'default_value', 'advanced_default_value', 'merge_key']
        csv = FileCsvWriter(output_file, fieldnames, encoding="utf-8", writeheader=True, delimiter=',', quotechar='"')
        current_file = self.browse(cr, uid, id, context=context)
        for field in current_file.field_ids:
            row = {
                'file_id:id': field.file_id.get_absolute_id(context=context),
                'name': field.name,
                'id': field.get_absolute_id(context=context),
                'sequence': str(field.sequence),
                'mappinglines_template_id:id': field.mapping_line_id and field.mapping_line_id.get_absolute_id(context=context) or '',
                'custom_name': field.custom_name or '',
                'default_value': field.default_value or '',
                'is_required': str(field.is_required),
                'advanced_default_value': field.advanced_default_value or '',
                'merge_key': str(field.merge_key),
            }
            csv.writerow(row)
        return self.pool.get('pop.up.file').open_output_file(cr, uid, 'file.fields.csv', output_file, 'File Exchange Fields Export', context=context)

    # Method to export the default fields file
    def create_file_default_fields(self, cr, uid, id, context=None):
        if isinstance(id,list):
            id = id[0]
        output_file = TemporaryFile('w+b')
        fieldnames = ['id', 'import_default_field:id', 'import_default_value', 'file_id:id', 'mapping_template_id:id', 'type']
        csv = FileCsvWriter(output_file, fieldnames, encoding="utf-8", writeheader=True, delimiter=',', quotechar='"')
        current_file = self.browse(cr, uid, id, context=context)
        for field in current_file.import_default_fields:
            row = {
                'id': field.get_absolute_id(context=context),
                'import_default_field:id': field.import_default_field.get_external_id(context=context)[field.import_default_field.id],
                'import_default_value': field.import_default_value,
                'file_id:id': current_file.get_absolute_id(context=context),
                'mapping_template_id:id': field.mapping_id.get_absolute_id(context=context),
                'type': field.type,
            }
            csv.writerow(row)
        return self.pool.get('pop.up.file').open_output_file(cr, uid, 'file.default.import.values.csv', output_file, 'File Exchange Fields Export', context=context)

    def load_mapping(self, cr, uid, ids, context=None):
        for method in self.browse(cr, uid, ids, context=context):
            mapping_id = self.pool.get('external.mapping').search(cr, uid, [('referential_id', '=', method.referential_id.id),('template_id', '=', method.mapping_template_id.id)], context=context)[0]
            self.write(cr, uid, method.id, {'mapping_id': mapping_id}, context=context)
            for default_field in method.import_default_fields:
                default_mapping_id = self.pool.get('external.mapping').search(cr, uid, [('referential_id', '=', method.referential_id.id),('template_id', '=', default_field.mapping_template_id.id)], context=context)[0]
                default_field.write({'mapping_id': default_mapping_id}, context=context)
            for field in method.field_ids:
                if field.mappinglines_template_id:
                    field_mapping_line_id = self.pool.get('external.mapping.line').search(cr, uid, [('referential_id', '=', method.referential_id.id),('template_id', '=', field.mappinglines_template_id.id)], context=context)[0]
                    field.write({'mapping_line_id': field_mapping_line_id}, context=context)
        return True


class file_fields(Model):
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
        'custom_name': fields.char('Custom Name', size=128),
        'sequence': fields.integer('Sequence', required=True, help="The sequence field is used to define the order of the fields"),
        #TODO add a filter only fields that belong to the main object or to sub-object should be available
        'mapping_line_id': fields.many2one('external.mapping.line', 'OpenERP Mapping', domain = "[('referential_id', '=', parent.referential_id),('mapping_id', 'in', parent.related_mapping_ids[0][2])]"),
        'file_id': fields.many2one('file.exchange', 'File Exchange', require="True"),
        'default_value': fields.char('Default Value', size=64),
        'advanced_default_value': fields.text('Advanced Default Value', help=("This python code will be evaluate and the value"
                                                                        "in the varaible result will be used as defaut value")),
        'alternative_key': fields.related('mapping_line_id', 'alternative_key', type='boolean', string='Alternative Key'),
        'is_required' : fields.boolean('Is required', help="Is this field required in the exchange ?"),
        'mappinglines_template_id':fields.many2one('external.mappinglines.template', 'External Mappinglines Template'),
        'merge_key': fields.boolean('Merge Key', help="Used to merge each line with the same value of this field")
    }

    def get_absolute_id(self, cr, uid, id, context=None):
        if isinstance(id,list):
            id = id[0]
        field = self.browse(cr, uid, id, context=context)
        field_id = field.get_external_id(context=context)[field.id]
        if not field_id:
            file_name = field.file_id.name.replace(' ','_')
            field_name = field.name
            sequence = str(field.sequence)
            field_id = (file_name + '_' + field_name + '_' + sequence).replace('.','_')
        return field_id


class file_default_import_values(Model):
    _name = "file.default.import.values"
    _description = "file default import values"

    _columns = {
        'import_default_field':fields.many2one('ir.model.fields', 'Default Field'),
        'import_default_value':fields.char('Default Value', size=128),
        'file_id': fields.many2one('file.exchange', 'File Exchange'),
        'mapping_id':fields.many2one('external.mapping', 'External Mapping'),
        'mapping_template_id':fields.many2one('external.mapping.template', 'External Mapping Template'),
        'type':fields.selection([('integer', 'Integer'), ('float', 'Float'),('char','String'),('dict','Dict'),('list','List')], 'Field Type'),
    }

    def get_absolute_id(self, cr, uid, id, context=None):
        if isinstance(id,list):
            id = id[0]
        field = self.browse(cr, uid, id, context=context)
        field_id = field.get_external_id(context=context)[field.id]
        if not field_id:
            file_name = field.file_id.name.replace(' ','_')
            field_name = field.import_default_field.name
            field_id = (file_name + '_' + field_name).replace('.','_')
        return field_id

    def on_change_models(self, cr, uid, ids, mapping_id=False, context=None):
        res = {}
        if mapping_id:
            mapping = self.pool.get('external.mapping').browse(cr, uid, mapping_id, context=context)
            models = [x for x in self.pool.get(mapping.model_id.model)._inherits]
            models.append(mapping.model_id.model)
            res['import_default_field'] = [('model', 'in', models)]
        return {'domain': res}
