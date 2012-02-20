# -*- encoding: utf-8 -*-
###############################################################################
#                                                                             #
#   ftp_external_referential for OpenERP                                      #
#   Copyright (C) 2011 Akretion Sébastien BEAU <sebastien.beau@akretion.com>  #
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

osv.osv._get_filter = _get_filter
osv.osv._get_default_import_values = _get_default_import_values

original_get_filter = osv.osv._get_filter
original__get_default_import_values = osv.osv._get_default_import_values



def _get_filter(self, cr, uid, external_session, step, previous_filter=None, context=None):
    if external_session.referential_id.type == 'file_exchange':
        file_exchange_id = context['file.exchange_id']
        self.pool
    return original_get_filter


class ftp_osv(osv.osv):
    
    _name = "ftp.osv"
    _description = "ftp osv"




ftp_osv()
