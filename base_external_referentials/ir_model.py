# -*- encoding: utf-8 -*-
###############################################################################
#                                                                             #
#   base_external_referentials for OpenERP                                    #
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


class ir_model(Model):
    _inherit='ir.model'

    def create_external_link(self, cr, uid, model_id, context=None):
        model = self.pool.get('ir.model').browse(cr, uid, model_id, context=context)
        vals = {'domain': "[('res_id', '=', active_id), ('model', '=', '%s')]" %(model.model,),
                'name': 'External %s'%(model.name),
                'res_model': 'ir.model.data',
                'src_model': model.model,
                'view_type': 'form',
                }
        xml_id = "ext_" + model.model.replace(".", "_")
        ir_model_data_id = self.pool.get('ir.model.data')._update(cr, uid,
                                                                  'ir.actions.act_window',
                                                                  "base_external_referentials",
                                                                  vals, xml_id, False, 'update')
        value = 'ir.actions.act_window,'+str(ir_model_data_id)
        return self.pool.get('ir.model.data').ir_set(cr, uid, 'action',
                                                     'client_action_relate',
                                                     xml_id, [model.model],
                                                     value, replace=True,
                                                     isobject=True,
                                                     xml_id=xml_id)

