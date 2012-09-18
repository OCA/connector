# -*- encoding: utf-8 -*-
#################################################################################
#                                                                               #
#    base_pop_up for OpenERP                                                    #
#    Copyright (C) 2011 Akretion Benoît Guillot <benoit.guillot@akretion.com>   #
#    Copyright (C) 2011 Akretion Sébastien BEAU <sebastien.beau@akretion.com>   #
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

from openerp.osv.orm import TransientModel
from osv import fields
import base64
from tempfile import TemporaryFile

class pop_up_file(TransientModel):
    _name = "pop.up.file"
    _description = "Output File"

    _columns = {
        'name': fields.char('Name', size=64),
        'file': fields.binary('File'),
    }

    def open_output_file(self, cr, uid, file_name, output_file, title, context=None):
        mod_obj = self.pool.get('ir.model.data')
        output_file.seek(0)
        file_data = base64.encodestring(output_file.read())
        output_object_id = self.pool.get('pop.up.file').create(cr, uid, {'name' : file_name, 'file' : file_data}, context=context)
        res = mod_obj.get_object_reference(cr, uid, 'base_pop_up', 'output_file_form_view')
        res_id = res and res[1] or False
        action = {
            'name': title,
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': [res_id],
            'res_model': 'pop.up.file',
            'type': 'ir.actions.act_window',
            'nodestroy': True,
            'target': 'new',
            'res_id': output_object_id,
            }
        return action

    def close(self, cr, uid, ids, context=None):
        self.unlink(cr, uid, ids, context=context)
        return {'type': 'ir.actions.act_window_close'}


    def open_input_file(self, cr, uid, title, callback, args, context=None):
        mod_obj = self.pool.get('ir.model.data')
        context['pop_up_callback'] = {
            'func_name': callback.func_name,
            'self': callback.__self__._name,
            'args': args,
            }
        input_object_id = self.pool.get('pop.up.file').create(cr, uid, {}, context=context)
        res = mod_obj.get_object_reference(cr, uid, 'base_pop_up', 'input_file_form_view')
        res_id = res and res[1] or False
        action = {
            'name': title,
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': [res_id],
            'res_model': 'pop.up.file',
            'type': 'ir.actions.act_window',
            'nodestroy': True,
            'target': 'new',
            'res_id': input_object_id,
            'context': context,
            }
        print 'open action', action
        return action

    def send(self, cr, uid, ids, context=None):
        callback_object = self.pool.get(context['pop_up_callback']['self'])
        callback_func_name = context['pop_up_callback']['func_name']
        callback_args = context['pop_up_callback']['args']
        wizard = self.browse(cr, uid, ids[0], context=context)
        input_file =TemporaryFile('w+b')
        input_file.write(base64.decodestring(wizard.file))
        input_file.seek(0)
        callback_args += [input_file, wizard.name]
        getattr(callback_object, callback_func_name)(*([cr, uid] + callback_args), context=context)
        return {'type': 'ir.actions.act_window_close'}


