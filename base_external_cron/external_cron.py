# -*- encoding: utf-8 -*-
###############################################################################
#                                                                             #
#   base_external_cron for OpenERP                                            #
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
import netsvc
from base_external_referentials.external_osv import ExternalSession
import sys
sys.path.append('/home/dav/dvp/py/ebay/ebaypyt/lib')
from ebaypyt import EbayWebService


class external_cron(osv.osv):

    _name = "external.cron"
    _description = "external.cron"


    _columns = {
        'name': fields.char('Name', size=50, required=True),
        'active': fields.boolean('Active', help="The active field allows to hide the item in tree view without deleting it."),
        'period': fields.selection((('month','Month'), ('week','Week'), ('day','Day'),
            ('minute','Minute')), 'Periodicity', help="Base unit periodicity used by cron"),
        'frequency': fields.integer('Frequency', help="Interval cron in minutes. Set periodicity on 'minute'"),
        'repeat': fields.datetime('Repeat',
            help="Recurrency selection with datetime widget : if 'periodicity' is 'day' only hour indicate the external data; if is 'week'  "),
        'report_type': fields.selection([('sale','Sale'), ('product','Product')],'Report', help="Report type name to cron"),
        'referential_id':fields.many2one('external.referential', 'Referential', help="External referential"),
    }

    _defaults = {
        'active': 1
    }

    # def external_unlink(self, cr, uid, ids, context=None):
        # model = self.pool.get('ir.model.data')
        # for cron in self.browse(cr, uid, ids, context=context):
            # irs = model.search(cr, uid, [('res_id','=',cron.id),('model','=','external.cron')])
            # for ext_cron in model.browse(cr, uid, irs, context=context):
                # referential = ext_cron.referential_id.id
                # ext_cron.unlink(cr, uid, ids, context=context)
                # external_session = ExternalSession(referential, referential)
                # external_session.connection.delete('RecurringJob', cron.name)

        # for cron in self.browse(cr, uid, ids, context=context):
            # recuoere les id externe et les referentiel
            # pr chaque ref
            # referential = 1
            # external_session = ExternalSession(referential, referential)
            # external_session.connection.delete('RecurringJob', cron.name)

    def action_test(self, cr, uid, ids, context=None):
        # TODO to delete
        developer_key   = "d7e26236-db06-4ad5-b050-228794d29228"
        application_key = "akretion-74cb-402c-b8b4-45cc8087b8a1"
        certificate_key = "9dbb492e-503d-47e0-9587-cc9ef0aab462"

        o_ext_ref = self.pool.get('external.referential')
        ext_ref_ids = o_ext_ref.search(cr, uid, [('name','=','ebay')])
        for ext_ref in o_ext_ref.browse(cr, uid, ext_ref_ids):
            print o_ext_ref._columns.keys()
            print ext_ref.__dict__
            print '    ext. referential ',ext_ref.id, ext_ref.name
            ews = EbayWebService(developer_key,application_key,certificate_key,ext_ref.ebay_auth_token)

        o_ir_model = self.pool.get('ir.model.data')
        # o_ext_cron = self.pool.get('external.cron')
        for cron in self.browse(cr, uid, ids, context=context):
            irs = o_ir_model.search(cr, uid, [('res_id','=',cron.id),('model','=','external.cron')])
            print '     cron.id :', cron.id, '     cron name:', cron.name
            for ext_cron in o_ir_model.browse(cr, uid, irs, context=context):
                print '     ext_cron.id :', ext_cron.id
                jobId = ext_cron.name[14:]
                un_ext_cron = o_ir_model.unlink(cr, uid, ext_cron.id, context=context)
                print '     unlink ext_cron :',un_ext_cron
                print '      job id :', jobId
                recc = ews.delete('RecurringJob', jobId)
            print '      cron deleted :', cron.id
            un_cron = self.unlink(cr, uid, cron.id, context=context)

            # print '     da cron:', cron
            # print '     da cron:', cron.referential_id
            # print '     da cron:', cron.referential_id.id
            # print '     da vers:', cron.referential_id.version_id
            # print '     da vers:', cron.referential_id.name
            # print '     da map:', cron.referential_id.mapping_ids
            # print '     da map name:', cron.referential_id.mapping_ids[0]
            # print '     da map get:', cron.referential_id.mapping_ids[0].external_get_method
            # print '     da mapping eval:', cron.referential_id.mapping_ids[0].mapping_ids[1].evaluation_type
            # print '     da in_function :', cron.referential_id.mapping_ids[0].mapping_ids[1].in_function

        return True


    def unlink(self, cr, uid, ids, context=None):
        self.ext_unlink(cr, uid, ids, context=context)
        return super(external_cron, self).unlink(cr, uid, ids, context=context)

