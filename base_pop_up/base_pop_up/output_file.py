# -*- encoding: utf-8 -*-
#################################################################################
#                                                                               #
#    base_pop_up for OpenERP                                          #
#    Copyright (C) 2011 Akretion Benoît Guillot <benoit.guillot@akretion.com>   #
#                                                                               #
#    This program is free software: you can redistribute it and/or modify       #
#    it under the terms of the GNU Affero General Public License as             #
#    published by the Free Software Foundation, either version 3 of the         #
#    License, or (at your option) any later version.                            #
#                                                                               #
#    This program is distributed in the hope that it will be useful,            #
#    but WITHOUT ANY WARRANTY; without even the implied warranty of             #
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the              #
#    GNU Affero General Public License for more details.                        #
#                                                                               #
#    You should have received a copy of the GNU Affero General Public License   #
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.      #
#                                                                               #
#################################################################################

from osv import osv, fields
import netsvc
import base64

class output_file(osv.osv_memory):
    _name = "output.file"
    _description = "Output File"

    _columns = {
        'name': fields.char('Name', size=64),
        'file': fields.binary('File'),
    }

    def open_output_file(self, cr, uid, file_name, output_file, title, context=None):
        output_file.seek(0)
        file_data = base64.encodestring(output_file.read())
        output_object_id = self.pool.get('output.file').create(cr, uid, {'name' : file_name, 'file' : file_data}, context=context)
        action = {
            'name': title,
            'view_type': 'form',
            'view_mode': 'form,tree',
            'view_id': False,
            'res_model': 'output.file',
            'type': 'ir.actions.act_window',
            'nodestroy': True,
            'target': 'new',
            'res_id': output_object_id,
            }
        return action

    def close(self, cr, uid, ids, context=None):
        self.unlink(cr, uid, ids, context=context)
        return {'type': 'ir.actions.act_window_close'}

