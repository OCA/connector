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

from osv import osv, fields
import netsvc
from base_external_referentials.external_osv import ExternalSession
import csv
from tempfile import TemporaryFile

class file_exchange(osv.osv):
    _name = "file.exchange"
    _description = "file exchange"

    def get_default_fields_values(self, cr, uid, id, context=None):
        if isinstance(id, list):
            id = id[0]
        res = {}
        method = self.browse(cr, uid, id, context=context)
        for field in method.field_ids:
            if field.default_value:
                res[field.name] = field.default_value
        return res

    def _get_external_file_resources(self, cr, uid, external_session, filepath, filename, format, fields_name=None, context=None):
        external_file = external_session.connection.get(filepath, filename)
        print 'format', format, format == 'csv_no_header'
        if format == 'csv_no_header':
            print 'no header'
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
        file_fields_obj = self.pool.get('file.fields')
        method = self.browse(cr, uid, method_id, context=context)
        defaults = self.get_default_fields_values(cr, uid, method_id, context=context)
        external_session = ExternalSession(method.referential_id)
        model_obj = self.pool.get(method.model_id.model)

        fields_name_ids = file_fields_obj.search(cr, uid, [['file_id', '=', method.id]], context=context)
        fields_info = file_fields_obj.read(cr, uid, fields_name_ids, ['name', 'mapping_line_id'], context=context)
        fields_to_read = [x['mapping_line_id'][1] for x in fields_info if x['mapping_line_id']]
        fields_name = [x['name'] for x in fields_info]

        #TODO add a filter
        ids_to_export = model_obj.search(cr, uid, [], context=context)

        mapping = {model_obj._name : model_obj._get_mapping(cr, uid, external_session.referential_id.id, mapping_type='out', context=context)}
        resources = model_obj._get_oe_resources_into_external_format(cr, uid, external_session, ids_to_export, mapping=mapping, fields=fields_to_read, defaults=defaults, context=context)
        if method.format == 'csv':
            #output_file = TemporaryFile('w+b')
            output_file = open("/tmp/output", 'w+b')
            fields_name = [x.encode('utf-8') for x in fields_name]
            dw = csv.DictWriter(output_file, fieldnames=fields_name, delimiter=';')
            dw.writeheader()
            for resource in resources:
                dw.writerow({k.encode('utf8'):v.encode('utf8') for k,v in resource.items()})
            output_file.seek(0)
        external_session.connection.send(method.folder_path, method.output_format, output_file)

        return True

    _columns = {
        'name': fields.char('Name', size=64, help="Exchange description like the name of the supplier, bank,..."),
        'type': fields.selection([('in','IN'),('out','OUT'),], 'Type',help=("IN for files coming from the other system"
                                                                "and to be imported in the ERP ; OUT for files to be"
                                                                "generated from the ERP and send to the other system")),
        'model_id':fields.many2one('ir.model', 'Model',help="OpenEPR main object from which all the fields will be related"),
        'format' : fields.selection([('csv','CSV'),('csv_no_header','CSV WITHOUT HEADER')], 'File format'),
        'referential_id':fields.many2one('external.referential', 'Referential',help="Referential to use for connection and mapping"),
        'scheduler_id':fields.many2one('ir.cron', 'Scheduler',help="Scheduler that will execute the cron task"),
        'output_format': fields.char('Output Format', size=128, help="Output Format will be used to generate the output file name"),
        'incomming_file': fields.char('Incomming File Name', size=128, help="Incomming file name that will be useed to define the file to import"),
        'folder_path': fields.char('Folder Path', size=128, help="folder that containt the incomming or the outgoing file"),
        'field_ids': fields.one2many('file.fields', 'file_id', 'Fields')
    }

file_exchange()


class file_fields(osv.osv):
    _name = "file.fields"
    _description = "file fields"
    _order='sequence'

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
        'mapping_line_id': fields.many2one('external.mapping.line', 'OpenERP Mapping'),
        'file_id': fields.many2one('file.exchange', 'File Exchange', require="True"),
        'default_value': fields.char('Default Value', size=64),
    }

file_fields()













