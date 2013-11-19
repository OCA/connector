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

import os
import logging
from datetime import datetime, timedelta

from openerp.osv import orm, fields
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp.tools.translate import _

from .job import STATES, DONE, PENDING, OpenERPJobStorage
from .worker import WORKER_TIMEOUT
from ..session import ConnectorSession
from .worker import watcher

_logger = logging.getLogger(__name__)


class QueueJob(orm.Model):
    """ Job status and result """
    _name = 'queue.job'
    _description = 'Queue Job'
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    _log_access = False

    _order = 'date_created DESC, date_done DESC'

    _removal_interval = 30  # days

    _columns = {
        'worker_id': fields.many2one('queue.worker', string='Worker',
                                     ondelete='set null', readonly=True),
        'uuid': fields.char('UUID', readonly=True, select=True, required=True),
        'user_id': fields.many2one('res.users', string='User ID', required=True),
        'name': fields.char('Description', readonly=True),
        'func_string': fields.char('Task', readonly=True),
        'func': fields.text('Pickled Function', readonly=True, required=True),
        'state': fields.selection(STATES,
                                  string='State',
                                  readonly=True,
                                  required=True),
        'priority': fields.integer('Priority'),
        'exc_info': fields.text('Exception Info', readonly=True),
        'result': fields.text('Result', readonly=True),
        'date_created': fields.datetime('Created Date', readonly=True),
        'date_started': fields.datetime('Start Date', readonly=True),
        'date_enqueued': fields.datetime('Enqueue Time', readonly=True),
        'date_done': fields.datetime('Date Done', readonly=True),
        'eta': fields.datetime('Execute only after'),
        'active': fields.boolean('Active'),
        'model_name': fields.char('Model', readonly=True),
        'retry': fields.integer('Current try'),
        'max_retries': fields.integer(
            'Max. retries',
            help="The job will fail if the number of tries reach the max. retries.\n"
                 "Retries are infinite when empty."),
    }

    _defaults = {
        'active': True,
    }

    def _change_job_state(self, cr, uid, ids, state, result=None, context=None):
        """ Change the state of the `Job` object itself so it
        will change the other fields (date, result, ...)
        """
        if not hasattr(ids, '__iter__'):
            ids = [ids]

        session = ConnectorSession(cr, uid, context=context)
        storage = OpenERPJobStorage(session)
        for job in self.browse(cr, uid, ids, context=context):
            job = storage.load(job.uuid)
            if state == DONE:
                job.set_done(result=result)
            elif state == PENDING:
                job.set_pending(result=result)
            else:
                raise ValueError('State not supported: %s' % state)
            storage.store(job)

    def button_done(self, cr, uid, ids, context=None):
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        result = _('Manually set to done by %s') % user.name
        self._change_job_state(cr, uid, ids, DONE,
                               result=result, context=context)
        return True

    def requeue(self, cr, uid, ids, context=None):
        self._change_job_state(cr, uid, ids, PENDING, context=context)
        return True

    def write(self, cr, uid, ids, vals, context=None):
        res = super(QueueJob, self).write(cr, uid, ids, vals, context=context)
        if vals.get('state') == 'failed':
            if not hasattr(ids, '__iter__'):
                ids = [ids]
            # subscribe the users now to avoid to subscribe them
            # at every job creation
            self._subscribe_users(cr, uid, ids, context=context)
            for id in ids:
                msg = self._message_failed_job(cr, uid, id, context=context)
                if msg:
                    self.message_post(cr, uid, id, body=msg,
                                      subtype='connector.mt_job_failed',
                                      context=context)
        return res

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

    def _message_failed_job(self, cr, uid, id, context=None):
        """ Return a message which will be posted on the job when it is failed.

        It can be inherited to allow more precise messages based on the
        exception informations.

        If nothing is returned, no message will be posted.
        """
        return _("Something bad happened during the execution of the job. "
                 "More details in the 'Exception Information' section.")

    def _needaction_domain_get(self, cr, uid, context=None):
        """ Returns the domain to filter records that require an action
            :return: domain or False is no action
        """
        return [('state', '=', 'failed')]

    def autovacuum(self, cr, uid, context=None):
        """ Delete all jobs (active or not) done since more than
        ``_removal_interval`` days.

        Called from a cron.
        """
        if context is None:
            context = {}
        context = dict(context, active_test=False)
        deadline = datetime.now() - timedelta(days=self._removal_interval)
        deadline_fmt = deadline.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        job_ids = self.search(cr, uid,
                              [('date_done', '<=', deadline_fmt)],
                              context=context)
        self.unlink(cr, uid, job_ids, context=context)
        return True


class QueueWorker(orm.Model):
    """ Worker """
    _name = 'queue.worker'
    _description = 'Queue Worker'
    _log_access = False
    _rec_name = 'uuid'

    worker_timeout = WORKER_TIMEOUT

    _columns = {
        'uuid': fields.char('UUID', readonly=True, select=True, required=True),
        'pid': fields.char('PID', readonly=True),
        'date_start': fields.datetime('Start Date', readonly=True),
        'date_alive': fields.datetime('Last Alive Check', readonly=True),
        'job_ids': fields.one2many('queue.job', 'worker_id',
                                   string='Jobs', readonly=True),
    }

    def _notify_alive(self, cr, uid, worker, context=None):
        worker_ids = self.search(cr, uid,
                                 [('uuid', '=', worker.uuid)],
                                 context=context)

        now_fmt = datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        if not worker_ids:
            self.create(cr, uid,
                        {'uuid': worker.uuid,
                         'pid': os.getpid(),
                         'date_start': now_fmt,
                         'date_alive': now_fmt},
                        context=context)
        else:
            self.write(cr, uid, worker_ids,
                       {'date_alive': now_fmt}, context=context)

    def _purge_dead_workers(self, cr, uid, context=None):
        deadline = datetime.now() - timedelta(seconds=self.worker_timeout)
        deadline_fmt = deadline.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        dead_ids = self.search(cr, uid,
                               [('date_alive', '<', deadline_fmt)],
                               context=context)
        dead_workers = self.read(cr, uid, dead_ids, ['uuid'], context=context)
        for worker in dead_workers:
            _logger.debug('Worker %s is dead', worker['uuid'])
        try:
            self.unlink(cr, uid, dead_ids, context=context)
        except Exception:
            _logger.debug("Failed attempt to unlink a dead worker, likely due "
                          "to another transaction in progress.")

    def _worker_id(self, cr, uid, context=None):
        worker = watcher.worker_for_db(cr.dbname)
        assert worker
        worker_ids = self.search(cr, uid, [('uuid', '=', worker.uuid)],
                                 context=context)
        assert len(worker_ids) == 1, ("%s worker found in database instead "
                                      "of 1" % len(worker_ids))
        return worker_ids[0]

    def assign_then_enqueue(self, cr, uid, max_jobs=None, context=None):
        """ Assign all the jobs not already assigned to a worker.
        Then enqueue all the jobs having a worker but not enqueued.

        Each operation is atomic.

        .. warning:: commit transaction
           ``cr.commit()`` is called, so please always call
           this method in your own transaction, not in the main
           OpenERP's transaction

        :param max_jobs: maximal limit of jobs to assign on a worker
        :type max_jobs: int
        """
        self.assign_jobs(cr, uid, max_jobs=max_jobs, context=context)
        cr.commit()
        self.enqueue_jobs(cr, uid, context=context)
        cr.commit()
        return True

    def assign_jobs(self, cr, uid, max_jobs=None, context=None):
        """ Assign ``n`` jobs to the worker of the current process

        ``n`` is ``max_jobs`` or unlimited if ``max_jobs`` is None

        :param max_jobs: maximal limit of jobs to assign on a worker
        :type max_jobs: int
        """
        worker = watcher.worker_for_db(cr.dbname)
        if worker:
            self._assign_jobs(cr, uid, max_jobs=max_jobs, context=context)
        else:
            _logger.debug('No worker started for process %s', os.getpid())
        return True

    def enqueue_jobs(self, cr, uid, context=None):
        """ Enqueue all the jobs assigned to the worker of the current
        process
        """
        worker = watcher.worker_for_db(cr.dbname)
        if worker:
            self._enqueue_jobs(cr, uid, context=context)
        else:
            _logger.debug('No worker started for process %s', os.getpid())
        return True

    def _assign_jobs(self, cr, uid, max_jobs=None, context=None):
        sql = ("SELECT id FROM queue_job "
               "WHERE worker_id IS NULL "
               "AND state not in ('failed', 'done') "
               "AND active = true "
               "ORDER BY eta NULLS LAST, priority, date_created ")
        if max_jobs is not None:
            sql += ' LIMIT %d' % max_jobs
        sql += ' FOR UPDATE NOWAIT'
        # use a SAVEPOINT to be able to rollback this part of the
        # transaction without failing the whole transaction if the LOCK
        # cannot be acquired
        worker = watcher.worker_for_db(cr.dbname)
        cr.execute("SAVEPOINT queue_assign_jobs")
        try:
            cr.execute(sql, log_exceptions=False)
        except Exception:
            # Here it's likely that the FOR UPDATE NOWAIT failed to get the LOCK,
            # so we ROLLBACK to the SAVEPOINT to restore the transaction to its earlier
            # state. The assign will be done the next time.
            cr.execute("ROLLBACK TO queue_assign_jobs")
            _logger.debug("Failed attempt to assign jobs, likely due to "
                          "another transaction in progress. "
                          "Trace of the failed assignment of jobs on worker "
                          "%s attempt: ", worker.uuid, exc_info=True)
            return
        job_rows = cr.fetchall()
        if not job_rows:
            _logger.debug('No job to assign to worker %s', worker.uuid)
            return
        job_ids = [id for id, in job_rows]

        worker_id = self._worker_id(cr, uid, context=context)
        _logger.debug('Assign %d jobs to worker %s', len(job_ids),
                      worker.uuid)
        # ready to be enqueued in the worker
        try:
            self.pool.get('queue.job').write(cr, uid, job_ids,
                                             {'state': 'pending',
                                             'worker_id': worker_id},
                                             context=context)
        except Exception:
            pass  # will be assigned to another worker

    def _enqueue_jobs(self, cr, uid, context=None):
        """ Add to the queue of the worker all the jobs not
        yet queued but already assigned."""
        job_obj = self.pool.get('queue.job')
        db_worker_id = self._worker_id(cr, uid, context=context)
        job_ids = job_obj.search(cr, uid,
                                 [('worker_id', '=', db_worker_id),
                                  ('state', '=', 'pending')],
                                 context=context)
        worker = watcher.worker_for_db(cr.dbname)
        jobs = job_obj.read(cr, uid, job_ids, ['uuid'], context=context)
        for job in jobs:
            worker.enqueue_job_uuid(job['uuid'])


class requeue_job(orm.TransientModel):
    _name = 'queue.requeue.job'
    _description = 'Wizard to requeue a selection of jobs'

    def _get_job_ids(self, cr, uid, context=None):
        if context is None:
            context = {}
        res = False
        if (context.get('active_model') == 'queue.job' and
                context.get('active_ids')):
            res = context['active_ids']
        return res

    _columns = {
        'job_ids': fields.many2many('queue.job', string='Jobs'),
    }

    _defaults = {
        'job_ids': _get_job_ids,
    }

    def requeue(self, cr, uid, ids, context=None):
        if isinstance(ids, (tuple, list)):
            assert len(ids) == 1, "One ID expected"
            ids = ids[0]

        form = self.browse(cr, uid, ids, context=context)
        job_ids = [job.id for job in form.job_ids]
        self.pool.get('queue.job').requeue(cr, uid, job_ids, context=context)
        return {'type': 'ir.actions.act_window_close'}
