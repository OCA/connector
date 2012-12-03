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

from openerp.osv.orm import Model, except_orm
from openerp.osv import fields
from tools.translate import _

#TODO refactor the constraint on ext_cron, this should be not harcoded
EXT_CRON_MINIMUM_FREQUENCY = 10 #in minute

#TODO rename the fields, do not mix frequency with period :S

class external_cron(Model):

    _name = "external.cron"
    _description = "external.cron"

    def _export_management_one_row(self, cr, uid, cron_id, field, arg, context=None):
        """ set exported et readonly value"""
        res = {}
        domain = [('model','=','external.cron'),('res_id','=',cron_id)]
        my_search = self.pool.get('ir.model.data').search(cr, uid, domain, context=context)
        if len(my_search) > 0:
            res[cron_id] = {'exported': True, 'readonly': False}
        else:
            res[cron_id] = {'exported': False, 'readonly': False}
        return res

    def _export_management(self, cr, uid, ids, field, arg, context=None):
        res={}
        for cron_id in ids:
            res.update(self._export_management_one_row(cr, uid, cron_id, field, arg, context=context))
        return res

    _columns = {
        'name': fields.char('Name', size=50, required=True),
        'active': fields.boolean('Active',
                help="The active field allows to hide the item in tree view without deleting it."),
        'period': fields.selection((('month','Month'), ('week','Week'), ('day','Day'),
            ('minute','Minute')), 'Periodicity', required=True,
                                                help="Base unit periodicity used by cron"),
        'frequency': fields.integer('Frequency (min.)',
                                    help="Interval cron in minutes if periodicity is in 'minutes'"),
        'repeat': fields.datetime('Repeat', help="Recurrency selection with datetime widget : \
                    if 'periodicity' is 'day' only hour indicate the external data; if is 'week'"),
        'report_type': fields.selection([('sale','Sale'), ('product','Product')],'Report',
                                            required=True,  help="Report type name to cron"),
        'referential_id':fields.many2one('external.referential', 'Referential', required=True,
                                                                    help="External referential"),
        'exported': fields.function(_export_management, multi='export', method=True, string='Exported', type='boolean',
                    help="True if cron has been exported to external application with success and subsequently has an external referential in 'ir.model.data'"),
        'readonly': fields.function(_export_management, multi='export', type='boolean', method=True, string='Read only', help='define form read only behavior'),
    }

    _defaults = {
        'active': 1,
        'name': 'external cron',
    }

#TODO refactor the constraint (only used by the prototype, ebayerpconnect)
    def _check_field_frequency(self, cr, uid, ids, context=None):
        for cron in self.browse(cr, uid, ids):
            if cron.frequency <= EXT_CRON_MINIMUM_FREQUENCY and cron.period == 'minute':
                raise except_orm(_('Invalid field value :'), _("'Frequency' field must be greater than %s minutes" %EXT_CRON_MINIMUM_FREQUENCY))
        return True

    def _count_duplicate_report(self, cr, uid, vals, context=None):
        domain = []
        for key, val in vals.items():
            domain.append((key, '=', val))
        domain.append(('active', '=', 'True'))
        return len(self.search(cr, uid, domain, context=context))

    def _check_field_active(self, cr, uid, ids, context=None):
        """ """
        for cron in self.browse(cr, uid, ids, context=context):
            vals = {'report_type': cron.report_type, 'referential_id': cron.referential_id.id}
            if cron.active == True:
                report_count = self._count_duplicate_report(cr, uid, vals, context=context)
                if report_count > 1:
                    raise except_orm(_('Too many reports of the same type for this referential:'),
                        _("There are %s 'Reports' of '%s' type  with 'active' value checked. \nOnly 1 is authorized!" % (report_count, cron.report_type)))
        return True

    def copy(self, cr, uid, id, default=None, context=None):
        row = self.browse(cr, uid, id, context=context)
        if default is None:
            default = {}
        default_custom={'exported': False, 'active': False, 'name': row.name+' copy'}
        default.update(default_custom)
        return super(external_cron, self).copy(cr, uid, id, default, context=context)

    _constraints = [
        (_check_field_frequency, "Error message in raise", ['frequency']),
        (_check_field_active, "Only one active cron per job", ['active']),
    ]

    def unlink(self, cr, uid, ids, context=None):
        self.ext_unlink(cr, uid, ids, context=context)
        return super(external_cron, self).unlink(cr, uid, ids, context=context)
