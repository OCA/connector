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

from openerp.osv.orm import Model
from openerp.osv import fields
import base64
from base_external_referentials.external_osv import ExternalSession

class file_buffer(Model):

    _name = "file.buffer"
    _description = "File Buffer"

    _columns = {
        'name': fields.char('Name', size=64),
        'file_id': fields.char('Exch. file', size=64, help="Exchange id file"),
        'state': fields.selection((('waiting','Waiting'), ('running','Running'), ('done','Done'),
                                                                        ('fail','Fail')), 'State'),
        'active': fields.boolean('Active'),
        'mapping_id': fields.many2one('external.mapping', 'Mapping'),
        'job_ended': fields.datetime('Job ended', help="GMT date given by external application"),
        'referential_id': fields.related('shop_id', 'referential_id', type='many2one',
                        relation='external.referential', string='Ext. referential', store=True),
        #This field add a dependency on sale (maybe move it into an other module if it's problematic)
        'shop_id': fields.many2one('sale.shop', 'Shop'),
        'direction': fields.selection([('input', 'Input'),('output', 'Output')], 'Direction',
                                      help='flow direction of the file'),
        'response': fields.text('Response', help='External application response'),
    }

    _order = 'job_ended desc'

    _defaults = {
        'active': 1,
        'state': 'waiting',
    }

    def get_file(self, cr, uid, file_buffer_id, context=None):
        """
        Fonction that return the content of the attachment
        :param int file_id : id of the file buffer
        :rtype: str
        :return: the content attachment
        """
        attach_obj = self.pool.get('ir.attachment')
        attachment_id = attach_obj.search(cr, uid, [('res_model','=','file.buffer'),
                                                                ('res_id','=', file_buffer_id)])
        if not attachment_id:
            return False
        else:
            attachment = attach_obj.browse(cr, uid, attachment_id[0], context=context)
            return base64.decodestring(attachment.datas)

    def create_file_buffer_attachment(self, cr, uid, file_buffer_id, datas, file_name,
                                      context=None, extension='csv', prefix_file_name='report'):
        """
        Create file attachment to file.buffer object
        :param int file_buffer_id:
        :param str datas: file content
        :param str file_id: file name component
        :param str extension: file extension
        :param str prefix_file_name:
        :rtype: boolean
        :return: True
        """
        if context is None: context = {} 
        context.update({'default_res_id': file_buffer_id, 'default_res_model': 'file.buffer'})
        datas_encoded = base64.encodestring(datas)
        attach_name = prefix_file_name + '_' + file_name + '.' + extension
        params_attachment = {'name': attach_name, 'datas': datas_encoded,
                                                                    'datas_fname': attach_name}
        attachment_id = self.pool.get('ir.attachment').create(cr, uid, params_attachment, context)

        return True

    def check_state_file_buffer_scheduler(self, cr, uid, domain=None, context=None):
        if not domain: domain = []
        domain.append(('state', '=', 'running'))
        ids = self.search(cr, uid, domain, context=context)
        if ids:
            return self.check_state(cr, uid, ids, context=context)
        return True

    def run_file_buffer_scheduler(self, cr, uid, domain=None, context=None):
        if not domain: domain = []
        domain.append(('state', '=', 'waiting'))
        ids = self.search(cr, uid, domain, context=context)
        if ids:
            return self.run(cr, uid, ids, context=context)
        return True

    def run(self, cr, uid, ids, context=None):
        """
        Run the process for each file buffer
        """
        if context is None: context = {}
        for filebuffer in self.browse(cr, uid, ids, context=context):
            external_session = ExternalSession(filebuffer.referential_id, filebuffer)
            self._run(cr, uid, external_session, filebuffer, context=context)
            if filebuffer.direction == 'input':
                filebuffer.done()
        return True

    def _run(self, cr, uid, external_session, filebuffer, context=None):
        filebuffer._set_state('running', context=context)

    def done(self, cr, uid, ids, context=None):
        self._set_state(cr, uid, ids, 'done', context=context)

    def _set_state(self, cr, uid, ids, state, context=None):
        for id in ids:
            self.write(cr, uid, id, {'state': state}, context=context)

    def check_state(self, cr, uid, ids, context=None):
        """ Inherit this function in your module """
        return True
