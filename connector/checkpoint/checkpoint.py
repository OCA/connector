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
The checkpoint is a model containing records to be reviewed by the end
users.  The connectors register records to verify so the user can check
them and flag them as reviewed.

A concrete use case is the import of new products from Magento. Once
they are imported, the user have to configure things like the supplier,
so they appears in this list.
"""

from openerp.osv import orm, fields
from openerp.tools.translate import _


class connector_checkpoint(orm.Model):
    _name = 'connector.checkpoint'
    _description = 'Connector Checkpoint'

    _inherit = ['mail.thread', 'ir.needaction_mixin']

    def _get_models(self, cr, uid, context=None):
        """ All models are allowed as reference, anyway the
        fields.reference are readonly. """
        model_obj = self.pool.get('ir.model')
        model_ids = model_obj.search(cr, uid, [], context=context)
        models = model_obj.read(cr, uid, model_ids,
                                ['model', 'name'], context=context)
        return [(m['model'], m['name']) for m in models]

    def _get_ref(self, cr, uid, ids, prop, unknow_none, context=None):
        res = {}
        for check in self.browse(cr, uid, ids, context=context):
            res[check.id] = check.model_id.model + ',' + str(check.record_id)
        return res

    def _get_record_name(self, cr, uid, ids, prop, unknow_none, context=None):
        res = {}
        for check in self.browse(cr, uid, ids, context=context):
            model_obj = self.pool.get(check.model_id.model)
            res[check.id] = model_obj.name_get(cr, uid, [check.record_id],
                                               context=context)[0][1]
        return res

    def _search_record(self, cr, uid, obj, name, args, context=None):
        ids = set()
        model_obj = self.pool.get('ir.model')
        sql = "SELECT DISTINCT model_id FROM connector_checkpoint"
        cr.execute(sql)
        model_ids = [row[0] for row in cr.fetchall()]
        models = model_obj.read(cr, uid, model_ids,
                                ['model'], context=context)

        for criteria in args:
            __, operator, value = criteria
            for model in models:
                model_id = model['id']
                model_name = model['model']
                model_obj = self.pool.get(model_name)
                results = model_obj.name_search(cr, uid,
                                                name=value,
                                                operator=operator,
                                                context=context)
                res_ids = [res[0] for res in results]
                check_ids = self.search(cr, uid,
                                        [('model_id', '=', model_id),
                                         ('record_id', 'in', res_ids)],
                                        context=context)
                ids.update(check_ids)
        if not ids:
            return [('id', '=', '0')]
        return [('id', 'in', tuple(ids))]

    _columns = {
        'record': fields.function(
            _get_ref,
            type='reference',
            string='Record',
            selection=_get_models,
            help="The record to review.",
            size=128,
            readonly=True),
        'name': fields.function(
            _get_record_name,
            fnct_search=_search_record,
            type='char',
            string='Record Name',
            help="Name of the record to review",
            readonly=True),
        'record_id': fields.integer('Record ID',
                                    required=True,
                                    readonly=True),
        'model_id': fields.many2one('ir.model',
                                    string='Model',
                                    required=True,
                                    readonly=True),
        'backend_id': fields.reference(
            'Imported from',
            selection=_get_models,
            size=128,
            readonly=True,
            required=True,
            help="The record has been imported from this backend",
            select=1),
        'state': fields.selection(
            [('need_review', 'Need Review'),
             ('reviewed', 'Reviewed')],
            'Status',
            required=True,
            readonly=True),
    }

    _defaults = {
        'state': 'need_review',
    }

    def reviewed(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids,
                          {'state': 'reviewed'},
                          context=context)

    def _subscribe_users(self, cr, uid, ids, context=None):
        """ Subscribe all users having the 'Connector Manager' group """
        group_ref = self.pool.get('ir.model.data').get_object_reference(
            cr, uid, 'connector', 'group_connector_manager')
        if not group_ref:
            return
        group_id = group_ref[1]
        user_ids = self.pool.get('res.users').search(
            cr, uid, [('groups_id', '=', group_id)], context=context)
        self.message_subscribe_users(cr, uid, ids,
                                     user_ids=user_ids,
                                     context=context)

    def create(self, cr, uid, vals, context=None):
        obj_id = super(connector_checkpoint, self).create(
            cr, uid, vals, context=context)
        self._subscribe_users(cr, uid, [obj_id], context=context)
        cp = self.browse(cr, uid, obj_id, context=context)
        msg = _('A %s needs a review.') % cp.model_id.name
        self.message_post(cr, uid, obj_id, body=msg,
                          subtype='mail.mt_comment',
                          context=context)
        return obj_id

    def create_from_name(self, cr, uid, model_name, record_id,
                         backend_model_name, backend_id, context=None):
        model_obj = self.pool.get('ir.model')
        model_ids = model_obj.search(cr, uid,
                                     [('model', '=', model_name)],
                                     context=context)
        assert model_ids, "The model %s does not exist" % model_name
        backend = backend_model_name + ',' + str(backend_id)
        return self.create(cr, uid,
                           {'model_id': model_ids[0],
                            'record_id': record_id,
                            'backend_id': backend},
                           context=context)

    def _needaction_domain_get(self, cr, uid, context=None):
        """ Returns the domain to filter records that require an action
            :return: domain or False is no action
        """
        return [('state', '=', 'need_review')]


def add_checkpoint(session, model_name, record_id,
                   backend_model_name, backend_id):
    cr, uid, context = session.cr, session.uid, session.context
    checkpoint_obj = session.pool['connector.checkpoint']
    return checkpoint_obj.create_from_name(cr, uid, model_name, record_id,
                                           backend_model_name, backend_id,
                                           context=context)


class connector_checkpoint_review(orm.TransientModel):
    _name = 'connector.checkpoint.review'
    _description = 'Checkpoints Review'

    def _get_checkpoint_ids(self, cr, uid, context=None):
        if context is None:
            context = {}
        res = False
        if (context.get('active_model') == 'connector.checkpoint' and
                context.get('active_ids')):
            res = context['active_ids']
        return res

    _columns = {
        'checkpoint_ids': fields.many2many(
            'connector.checkpoint',
            'connector_checkpoint_review_rel',
            'review_id', 'checkpoint_id',
            string='Checkpoints',
            domain="[('state', '=', 'need_review')]"),
    }

    _defaults = {
        'checkpoint_ids': _get_checkpoint_ids,
    }

    def review(self, cr, uid, ids, context=None):
        if isinstance(ids, (tuple, list)):
            assert len(ids) == 1, "One ID expected"
            ids = ids[0]

        form = self.browse(cr, uid, ids, context=context)
        checkpoint_ids = [checkpoint.id for checkpoint in form.checkpoint_ids]
        checkpoint_obj = self.pool['connector.checkpoint']
        checkpoint_obj.reviewed(cr, uid, checkpoint_ids, context=context)
        return {'type': 'ir.actions.act_window_close'}
