# -*- encoding: utf-8 -*-
################################################################################
#                                                                              #
#    base_onchange_player for OpenERP                                          #
#    Copyright (C) 2011 Akretion Sébastien BEAU <sebastien.beau@akretion.com>  #
#                                                                              #
#    This program is free software: you can redistribute it and/or modify      #
#    it under the terms of the GNU Affero General Public License as            #
#    published by the Free Software Foundation, either version 3 of the        #
#    License, or (at your option) any later version.                           #
#                                                                              #
#    This program is distributed in the hope that it will be useful,           #
#    but WITHOUT ANY WARRANTY; without even the implied warranty of            #
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the             #
#    GNU Affero General Public License for more details.                       #
#                                                                              #
#    You should have received a copy of the GNU Affero General Public License  #
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.     #
#                                                                              #
################################################################################

from osv import osv
import netsvc
from tools.translate import _

def call_onchange(self, cr, uid, onchange_name, vals, **kwargs):
    """
    Used in base_sale_multichannel in order to call onchange method on sale_order_line and sale_order
    In order to call onchange you must have to create a function "_get_kwargs_my_onchange_name"
    that will return the kwargs for your onchange

    @param onchange_name: string that contain the onchange method to call
    @return: dictionary of line updated with the value returned by the onchange
    """
    try :
        kwargs2 = eval("self._get_kwargs_%s"%onchange_name)(cr, uid, vals, **kwargs)
    except Exception, e:
        raise osv.except_osv(_('On Change Player'), _("Error when trying to get the kwargs for the onchange %s on \
                                                    the object %s. Error message : %s" %(onchange_name, self._name, e)))
    try :
        res = eval("self.%s"%onchange_name)(cr, uid, **kwargs2)
        for key in res['value']:
            if not key in vals:
                vals[key] = res['value'][key]
    except Exception, e:
        raise osv.except_osv(_('On Change Player'), _("Error when trying to playing the onchange %s on the object %s. \
                                                                Error message : %s" %(onchange_name, self._name, e)))
    return vals

osv.osv.call_onchange = call_onchange
