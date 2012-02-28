    # -*- encoding: utf-8 -*-
###############################################################################
#                                                                             #
#   file_exchange for OpenERP                                                 #
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
from base_file_protocole.base_file_protocole import FileConnection
from tools.translate import _

class external_referential(osv.osv):
    _inherit = "external.referential"

    def external_connection_backport(self, cr, uid, id, debug=False, context=None):
        if isinstance(id, list):
            id=id[0]
        referential = self.browse(cr, uid, id, context=context)
        try:
            return FileConnection(referential.protocole, referential.location, referential.apiusername, referential.apipass)
        except Exception, e:
            raise osv.except_osv(_("Connection Error"), _("Could not connect to server\nCheck url & user & password.\n %s"%e))

    _columns={
        'protocole': fields.selection([('ftp','ftp'), ('filestore', 'Filestore')], 'Protocole'),
    }

external_referential()

