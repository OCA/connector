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
from base_external_referentials.decorator import only_for_referential
import netsvc

osv.osv._feo_record_one_external_resource = osv.osv._record_one_external_resource #feo mean file_exchange_original

@only_for_referential(ref_categ ='File Exchange', super_function = osv.osv._feo_record_one_external_resource)
def _record_one_external_resource(self, cr, uid, external_session, resource, **kwargs):
    context=kwargs.get('context')
    method = self.pool.get('file.exchange').browse(cr, uid, context['file_exchange_id'], context=context)
    method.start_action('action_before_each', self, None, resource, context=context)
    res = self._feo_record_one_external_resource(cr, uid, external_session, resource, **kwargs)
    res_id = res.get('create_id', False) or res.get('write_id', False)
    method.start_action('action_after_each', self, [res_id], resource, context=context)
    return res

osv.osv._record_one_external_resource = _record_one_external_resource

osv.osv._feo_get_default_import_values = osv.osv._get_default_import_values #feo mean file_exchange_original

@only_for_referential(ref_categ ='File Exchange', super_function = osv.osv._feo_get_default_import_values)
def _get_default_import_values(self, cr, uid, external_session, mapping_id, defaults=None, context=None):

    return res

osv.osv._get_default_import_values = _get_default_import_values
