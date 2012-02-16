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
        'name': fields.char('Name', size=64),
        'external_id':fields.many2one('external.referential', 'Referential'),
        'scheduler_id':fields.many2one('ir.cron', 'Scheduler'),
        'file_ids': fields.one2many('external_file', 'Field relation id', ''),
    }

    _defaults = {

    }

file_exchange()

#=====
class external_file(osv.osv):
    
    _name = "external.file"
    _description = "external file"

    _columns = {
        'name': fields.char('Name', size=64),
        'type': fields.boolean('Type'),
        'model_id':fields.many2one('ir.model', 'Model'),
        'format' : fields.selection([('csv','CSV'),], 'File format'),
    }

    _defaults = {

    }

external_file()
