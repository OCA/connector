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

"""
The checkpoint is a model containing records to be verified by the end
users.  The connectors register records to verify so the user can check
them and flag them as verified.

A concrete use case is the import of new products from Magento. Once
they are imported, the user have to configure things like the supplier,
so they appears in this list.
"""

from openerp.osv import orm, fields


class connector_checkpoint(orm.Model):
    _name = 'connector.checkpoint'
    _description = 'Connector Checkpoint'

    _rec_name = 'res_id'

    def _get_models(self, cr, uid, context=None):
        """ All models are allowed as reference, anyway the
        fields.reference are readonly. """
        model_obj = self.pool.get('ir.model')
        model_ids = model_obj.search(cr, uid, [], context=context)
        models = model_obj.read(cr, uid, model_ids,
                                ['model', 'name'], context=context)
        return [(m['model'], m['name']) for m in models]

    _columns = {
        'res_id': fields.reference(
            'Record',
            selection=_get_models,
            size=128,
            help="The record to check.",
            required=True,
            readonly=True,
            select=1),
        'backend_id': fields.reference(
            'Backend',
            selection=_get_models,
            size=128,
            readonly=True,
            required=True,
            help="The record has been imported from this backend",
            select=1),
        'state': fields.selection(
            [('pending', 'Pending'),
             ('done', 'Done')],
            'Status',
            required=True,
            readonly=True),
    }

    _defaults = {
        'state': 'pending',
    }
