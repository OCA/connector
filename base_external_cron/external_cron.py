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

    def unlink(self, cr, uid, ids, context=None):
        self.ext_unlink(cr, uid, ids, context=context)
        return super(external_cron, self).unlink(cr, uid, ids, context=context)

