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

from .job import STATES
from ..session import ConnectorSessionHandler

_logger = logging.getLogger(__name__)


class QueueJob(orm.Model):
    """ Job status and result """
    _name = 'queue.job'
    _log_access = False

    _order = 'date_created DESC, date_done DESC'

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
        'only_after': fields.datetime('Execute only after'),
        }

    def requeue(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state': 'pending'}, context=context)
        return True


class QueueWorker(orm.Model):
    """ Worker """
    _name = 'queue.worker'
    _log_access = False
    _rec_name = 'uuid'

    # worker_timeout = 5 * 60  # seconds
    # FIXME: remove test with shorten timeout
    worker_timeout = 20  # seconds
    _worker = None

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
            self._worker = worker
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
            # exists in self._workers only for the same process and pool
            if worker['uuid'] == self._worker:
                _logger.error('Worker %s should be alive, '
                              'but appears to be dead.',
                              worker['uuid'])
                self._worker = None
        # it will set worker_id to null on jobs, freeing them for
        # another worker
        self.unlink(cr, uid, dead_ids, context=context)

    def _worker_id(self, cr, uid, context=None):
        assert self._worker
        worker_ids = self.search(cr, uid, [('uuid', '=', self._worker.uuid)],
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
        if self._worker:
            self._assign_jobs(cr, uid, max_jobs=max_jobs, context=context)
        else:
            _logger.debug('No worker started for process %s', os.getpid())
        return True

    def enqueue_jobs(self, cr, uid, context=None):
        """ Enqueue all the jobs assigned to the worker of the current
        process
        """
        if self._worker:
            self._enqueue_jobs(cr, uid, context=context)
        else:
            _logger.debug('No worker started for process %s', os.getpid())
        return True

    def _assign_jobs(self, cr, uid, max_jobs=None, context=None):
        sql = ("SELECT id FROM queue_job "
               "WHERE worker_id IS NULL "
               "AND state not in ('failed', 'done') ")
        if max_jobs is not None:
            sql += ' LIMIT %d' % max_jobs
        sql += ' FOR UPDATE NOWAIT'
        # use a SAVEPOINT to be able to rollback this part of the
        # transaction without failing the whole transaction if the LOCK
        # cannot be acquired
        cr.execute("SAVEPOINT queue_assign_jobs")
        try:
            cr.execute(sql, log_exceptions=False)
        except Exception:
            # Here it's likely that the FOR UPDATE NOWAIT failed to get the LOCK,
            # so we ROLLBACK to the SAVEPOINT to restore the transaction to its earlier
            # state. The assign will be done the next time.
            cr.execute("ROLLBACK TO queue_assign_jobs")
            _logger.warning("Failed attempt to assign jobs, likely due "
                            "to another transaction already in progress. Next "
                            "attempt is likely to work. Detailed error "
                            "available at DEBUG level.")
            _logger.debug("Trace of the failed assignment of jobs on worker "
                          "%s attempt: ", self._worker.uuid, exc_info=True)
        job_rows = cr.fetchall()
        if not job_rows:
            _logger.debug('No job to assign to worker %s', self._worker.uuid)
            return
        job_ids = [id for id, in job_rows]

        worker_id = self._worker_id(cr, uid, context=context)
        _logger.debug('Assign %d jobs to worker %s', len(job_ids),
                      self._worker.uuid)
        self.pool.get('queue.job').write(cr, uid, job_ids,
                                         {'state': 'pending',
                                          'worker_id': worker_id},
                                         context=context)

    def _enqueue_jobs(self, cr, uid, context=None):
        """ Called by an ir.cron, add to the queue all the jobs not
        already queued"""
        db_worker_id = self._worker_id(cr, uid, context=context)
        db_worker = self.browse(cr, uid, db_worker_id, context=context)
        for job in db_worker.job_ids:
            if job.state == 'pending':
                self._worker.enqueue_job_uuid(job.uuid)


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
