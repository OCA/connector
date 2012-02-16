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

#=====
class file_exchange(osv.osv):
    
    _name = "file.exchange"
    _description = "file exchange"

    def import_files(self, cr, uid, ids, context=None) :
        return True

    def export_files(self, cr, uid, ids, context=None) :
        return True

    _columns = {
        'name': fields.char('Name', size=64,help="Exchange description like the name of the supplier, bank,..."),
        'external_id':fields.many2one('external.referential', 'Referential',help="Referential to use for connection and mapping"),
        'scheduler_id':fields.many2one('ir.cron', 'Scheduler',help="Scheduler that will execute the cron task"),
        'file_ids': fields.one2many('external.file', 'related_file_id', 'Files',help="List of files to be exchanged"),
    }

    _defaults = {

    }

file_exchange()

#=====
class external_file(osv.osv):
    
    _name = "external.file"
    _description = "external file"

    _columns = {
        'related_file_id' : fields.many2one('file.exchange', 'File'),
        'name': fields.char('Name', size=64,help="Name of the file which is also the standard naming for the exchange"),
        'type': fields.selection([('in','IN'),
                                    ('out','OUT'),], 'Type',help="IN for files coming from the other system and to be imported in the ERP ; OUT for files to be generated from the ERP and send to the other system"),
        'model_id':fields.many2one('ir.model', 'Model',help="OpenEPR main object from which all the fields will be related"),
        'format' : fields.selection([('csv','CSV'),], 'File format'),
        'fields_ids': fields.many2many('ir.model.fields', 'fields_and_files_rel', 'external_file.file_id', 'fields_id', 'Fields',help="list of the fields used in the file"),
    }

    _defaults = {

    }

external_file()
