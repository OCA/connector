# -*- encoding: utf-8 -*-
###############################################################################
#                                                                             #
#   file_exchange for OpenERP                                  #
#   Copyright (C) 2012 Akretion Emmanuel Samyn <emmanuel.samyn@akretion.com>   #
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

class file_exchange(osv.osv):
    _name = "file.exchange"
    _description = "file exchange"

    def import_files(self, cr, uid, ids, context=None) :
        return True

    def export_files(self, cr, uid, ids, context=None) :
        return True

    _columns = {
        'name': fields.char('Name', size=64, help="Exchange description like the name of the supplier, bank,..."),
        'type': fields.selection([('in','IN'),('out','OUT'),], 'Type',help=("IN for files coming from the other system"
                                                                "and to be imported in the ERP ; OUT for files to be"
                                                                "generated from the ERP and send to the other system")),
        'model_id':fields.many2one('ir.model', 'Model',help="OpenEPR main object from which all the fields will be related"),
        'format' : fields.selection([('csv','CSV'),('csv_no_header','CSV WITHOUT HEADER')], 'File format'),
        'external_id':fields.many2one('external.referential', 'Referential',help="Referential to use for connection and mapping"),
        'scheduler_id':fields.many2one('ir.cron', 'Scheduler',help="Scheduler that will execute the cron task"),
        'output_format': fields.char('Output Format', size=128, help="Output Format will be used to generate the output file name"),
        'incomming_filter': fields.char('Incomming Filter', size=128, help="Incomming filter that will be useed to define the file to import"),
        'folder_path': fields.char('Folder Path', size=128, help="folder that containt the incomming or the outgoing file"),
        'file_fields_ids': fields.one2many('file.fields', 'file_id', 'Fields')
    }

file_exchange()


class file_fields(osv.osv):
    _name = "file.fields"
    _description = "file fields"

    _columns = {
        #TODO the field name should be autocompleted bey the external field when selecting a mapping
        'name': fields.char('Name', size=64),
        'sequence': fields.integer('Sequence', required=True, help="The sequence field is used to define the order of the fields"),
        #TODO add a filter only fields that belong to the main object or to sub-object should be available
        'mapping_line_id': fields.many2one('external.mapping.line', 'OpenERP Mapping', require="True"),
        'file_id': fields.many2one('file.exchange', 'File Exchange', require="True"),
    }

file_fields()













