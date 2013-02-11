# -*- coding: utf-8 -*-
##############################################################################
#
#    Author: Guewen Baconnier
#    Copyright 2012 Camptocamp SA
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

from ..session import ConnectorSession


class QueueJob(orm.Model):
    """ Job status and result """
    _name = 'queue.job'

    _log_access = False

    _columns = {
        'worker_id': fields.many2one('queue.worker', string='Worker',
                                     readonly=True),
        'uuid': fields.char('UUID', readonly=True, select=True),
        'user_id': fields.integer('User ID'),
        'name': fields.char('Description', readonly=True),
        'func_string': fields.char('Task', readonly=True),
        'func': fields.text('Pickled Job Function', readonly=True),
        'state': fields.selection([('pending', 'Pending'),
                                   ('queued', 'Queued'),
                                   ('started', 'Started'),
                                   ('failed', 'Failed'),
                                   ('done', 'Done')],
                                  string='State',
                                  readonly=True),
        'exc_info': fields.text('Exception Info', readonly=True),
        'date_created': fields.datetime('Created Date', readonly=True),
        'date_started': fields.datetime('Start Date', readonly=True),
        'date_enqueued': fields.datetime('Enqueue Time', readonly=True),
        'date_done': fields.datetime('Date Done', readonly=True),
        'only_after': fields.datetime('Execute only after'),
        }

    def requeue(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state': 'pending'}, context=context)
        return True


class QueueWorker(orm.Model):
    """ Worker """

    _name = 'queue.worker'

    _log_access = False

    _columns = {
        'uuid': fields.char('UUID', readonly=True, select=True),
        }
