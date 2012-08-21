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

from openerp.osv.orm import Model
from base_external_referentials.decorator import only_for_referential, catch_error_in_report

Model._feo_record_one_external_resource = Model._record_one_external_resource #feo mean file_exchange_original

@only_for_referential(ref_categ ='File Exchange', super_function = Model._feo_record_one_external_resource)
@catch_error_in_report
def _record_one_external_resource(self, cr, uid, external_session, resource, **kwargs):
    context=kwargs.get('context')
    method = self.pool.get('file.exchange').browse(cr, uid, context['file_exchange_id'], context=context)
    check = method.start_action('check_if_import', self, None, resource, context=context)
    res = {}
    if check:
        method.start_action('action_before_each', self, None, resource, context=context)
        res = self._feo_record_one_external_resource(cr, uid, external_session, resource, **kwargs)
        res_id = res.get('create_id', False) or res.get('write_id', False)
        if res_id:
            method.start_action('action_after_each', self, [res_id], resource, context=context)
    return res

Model._record_one_external_resource = _record_one_external_resource

Model._feo_get_default_import_values = Model._get_default_import_values #feo mean file_exchange_original

@only_for_referential(ref_categ ='File Exchange', super_function = Model._feo_get_default_import_values)
def _get_default_import_values(self, cr, uid, external_session, mapping_id=None, defaults=None, context=None):
    if not defaults:
        defaults = {}
    method = external_session.sync_from_object
    mapping = self.pool.get('external.mapping').browse(cr, uid, mapping_id, context=context)
    for field in method.import_default_fields:
        if field.mapping_id.id == mapping.id:
            if field.type == 'integer':
                defaults[field.import_default_field.name] = int(field.import_default_value)
            elif field.type == 'float':
                defaults[field.import_default_field.name] = float(field.import_default_value.replace(',','.'))
            elif field.type in ['list','dict']:
                defaults[field.import_default_field.name] = eval(field.import_default_value)
            else:
                defaults[field.import_default_field.name] = str(field.import_default_value)
    return defaults

Model._get_default_import_values = _get_default_import_values

def _get_oe_resources_into_external_format(self, cr, uid, external_session, ids, mapping=None, mapping_id=None, mapping_line_filter_ids=None, fields=[], defaults=None, context=None):
    result = []
    for resource in self.read_w_order(cr, uid, ids, fields, context):
        result.append(self._transform_one_resource(cr, uid, external_session, 'from_openerp_to_external', resource, mapping, mapping_id, mapping_line_filter_ids=mapping_line_filter_ids, parent_data=None, previous_result=None, defaults=defaults, context=context))
    return result
Model._get_oe_resources_into_external_format = _get_oe_resources_into_external_format

