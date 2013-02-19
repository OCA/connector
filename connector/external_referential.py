# -*- coding: utf-8 -*-
##############################################################################
#
#    Author: Guewen Baconnier
#    Copyright 2013 Camptocamp SA
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp.osv import orm, fields


# name of the models usable by external.referential
available_backends = []
def add_backend(name):
    if not name in available_backends:
        available_backends.append(name)


class external_referential(orm.Model):
    _name = 'external.referential'
    _description = 'External Referential'

    def _select_backends(self, cr, uid, context=None):
        model_obj = self.pool.get('ir.model')
        ids = model_obj.search(cr, uid,
                               [('name', 'in', available_backends)],
                               context=context)
        res = model_obj.read(cr, uid, ids, ['model', 'name'], context=context)
        return [(r['model'], r['name']) for r in res]

    _columns = {
        'name': fields.char('Name', required=True),
        'backend_id': fields.reference(
            'External Backend',
            selection=_select_backends,
            required=True,
            size=128),
        'type': fields.related(
            'backend_id',
            'type',
            type='char',
            string='Type',
            readonly=True),
    }

    def _test_dot_in_name(self, cr, uid, ids, context=None):
        for referential in self.browse(cr, uid, ids):
            if '.' in referential.name:
                return False
        return True

    _constraints = [
        (_test_dot_in_name, 'The name cannot contain a dot.', ['name']),
    ]

    _sql_constraints = [
        ('name_uniq', 'unique (name)', 'Referential names must be unique !')
    ]


class external_backend(orm.AbstractModel):
    """ An instance of an external backend to synchronize with.

    The backends have to inherited this model in the connectors modules.
    """
    _name = 'external.backend'

    _columns = {
        'name': fields.char('Name', required=True),
        'type': fields.char('Type', readonly=True)
    }


class ir_model_data(orm.Model):
    _inherit = 'ir.model.data'

    _columns = {
        'referential_id':fields.many2one(
            'external.referential',
            'External Referential'),
    }

    _sql_constraints = [
        ('external_reference_uniq_per_object',
         'unique(model, res_id, referential_id)',
         'You cannot have on record with multiple external '
         'id for a same referential'),
    ]


from .deprecated.external_referentials import *
