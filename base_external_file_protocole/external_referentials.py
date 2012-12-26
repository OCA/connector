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

from openerp.osv.orm import Model
from openerp.osv import fields
from openerp.osv.osv import except_osv
from base_file_protocole.base_file_protocole import FileConnection
from tools.translate import _
from base_external_referentials.external_referentials import REF_VISIBLE_FIELDS

REF_VISIBLE_FIELDS.update({
    'SFTP': ['location', 'apiusername', 'apipass'],
    'FTP': ['location', 'apiusername', 'apipass'],
})



class external_referential(Model):
    _inherit = "external.referential"

    def external_connection(self, cr, uid, id, debug=False, logger=False, context=None):
        if isinstance(id, list):
            id=id[0]
        referential = self.browse(cr, uid, id, context=context)
        try:
            return FileConnection(referential.type_id.code, referential.location, referential.apiusername,\
                            referential.apipass, port=referential. port, allow_dir_creation = True, \
                            home_folder=referential.home_folder)
        except Exception, e:
            raise except_osv(_("Base File Protocole Connection Error"),
                             _("Could not connect to server\nCheck url & user & password.\n %s") % e)

    _columns={
        'port': fields.integer('Port'),
        'home_folder': fields.char('Home Folder', size=64),
    }

    def _prepare_external_referential_fieldnames(self, cr, uid, context=None):
        res = super(external_referential, self)._prepare_external_referential_fieldnames(cr, uid, context=context)
        res.append('protocole')
        return res

    def _prepare_external_referential_vals(self, cr, uid, referential, context=None):
        res = super(external_referential, self)._prepare_external_referential_vals(cr, uid, referential, context=context)
        res['protocole'] = referential.protocole
        return res

