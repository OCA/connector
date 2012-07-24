# -*- encoding: utf-8 -*-
###############################################################################
#                                                                             #
#   file_buffer for OpenERP                                                   #
#   Copyright (C) 2012 Akretion David BEAL <david.beal@akretion.com>           #
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
import base64

class file_buffer(osv.osv):

    _name = "file.buffer"
    _description = "File Buffer"


    _columns = {
        'name': fields.char('Name', size=64),
        'file_id': fields.char('Ext. file', size=64),
        'state': fields.selection((('waiting','Waiting'), ('running','Running'), ('done','Done')), 'State'),
        'active': fields.boolean('Active'),
        'mapping_id': fields.many2one('external.mapping', 'Mapping',
            help=""),
        'job_ended': fields.datetime('Job ended'),
        'referential_id': fields.related('mapping_id', 'referential_id', type='many2one', relation='external.referential', string='Ext. referential', store=True),
    }

    _order = 'name desc'

    _defaults = {
        'active': 1,
        'state': 'waiting',
    }

    def import_file():
        '''
        method qui import le fichier, on a tout ce qu’il faut, via le mapping on sait quel mapping on    doit appliqué et sur quel resource on applique l’import (product.product...)
        '''
        return True

    def get_file(self, cr, uid, file_id, context=None):
        """
        Blabla
        :param int file_id: mystr
        :param list mlist: mylist
        :rtype: str
        :return: __
        """


        attach_obj = self.pool.get('ir.attachment')
        attachment_id = attach_obj.search(cr, uid, [('res_model','=','file.buffer'), ('res_id','=', file_id)])
        if not attachment_id:
            return False
        else:
            attachment = attach_obj.browse(cr, uid, attachment_id[0], context=context)

            return base64.decodestring(attachment.datas)


    def run(self, cr, uid, ids, context=None):
        self._set_state(cr, uid, ids, 'running', context=context)

    def done(self, cr, uid, id, context=None):
        self._set_state(cr, uid, ids, 'done', context=context)

    def _set_state(self, cr, uid, ids, state, context=None):
        for id in ids:
            self.write(cr, uid, id, {'state': state}, context=context)
