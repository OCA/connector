# -*- encoding: utf-8 -*-
###############################################################################
#                                                                             #
#   report_synchronizer for OpenERP                                           #
#   Copyright (C) 2012 Akretion Sébastien BEAU <sebastien.beau@akretion.com>  #
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
import netsvc
from base_external_referentials.external_osv import extend
from tempfile import TemporaryFile

@extend(Model)
def send_report(self, cr, uid, external_session, ids, report_name, file_name, path, add_extension=True, context=None):
    service = netsvc.LocalService(report_name)
    result, format = service.create(cr, uid, ids, {'model': self._name}, context=context)
    output_file = TemporaryFile('w+b')
    output_file.write(result)
    output_file.seek(0)
    if add_extension:
        file_name = "%s.%s"%(file_name, format)
    external_session.connection.send(path, file_name, output_file)
    return file_name

