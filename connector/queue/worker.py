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

import logging
import os
import threading
import time
import traceback
import uuid
from datetime import datetime
from StringIO import StringIO

from psycopg2 import OperationalError, ProgrammingError

import openerp
from openerp.osv.osv import PG_CONCURRENCY_ERRORS_TO_RETRY
from openerp.tools import config
from .queue import JobsQueue
from ..session import ConnectorSessionHandler
from .job import (OpenERPJobStorage,
                  PENDING,
                  DONE)
from ..exception import (NoSuchJobError,
                         NotReadableJobError,
                         RetryableJobError,
                         FailedJobError,
                         NothingToDoJob)

_logger = logging.getLogger(__name__)

WAIT_CHECK_WORKER_ALIVE = 30  # seconds
WAIT_WHEN_ONLY_AFTER_JOBS = 10  # seconds
WORKER_TIMEOUT = 5 * 60  # seconds
PG_RETRY = 5  # seconds


class Worker(threading.Thread):
    """ Post and retrieve jobs from the queue, execute them"""

    queue_class = JobsQueue
    job_storage_class = OpenERPJobStorage

    def __init__(self, db_name, watcher):
        super(Worker, self).__init__()
        self.queue = self.queue_class()
        self.db_name = db_name
        threading.current_thread().dbname = db_name
        self.uuid = unicode(uuid.uuid4())
        self.watcher = watcher

    def run_job(self, job):
        """ Execute a job """
        def retry_postpone(job, message, seconds=None):
            with session_hdl.session() as session:
                job.postpone(result=message, seconds=seconds)
                job.set_enqueued(self)
                self.job_storage_class(session).store(job)
            self.queue.enqueue(job)

        session_hdl = ConnectorSessionHandler(self.db_name,
                                              openerp.SUPERUSER_ID)
        try:
            with session_hdl.session() as session:
                job = self._load_job(session, job.uuid)
                if job is None:
                    return

            # if the job has been manually set to DONE or PENDING
            # before its execution, stop
            if job.state in (DONE, PENDING):
                return

            # the job has been enqueued in this worker but has likely be
            # modified in the database since its enqueue
            if job.worker_uuid != self.uuid:
                # put the job in pending so it can be requeued
                _logger.error('Job %s was enqueued in worker %s but '
                              'was linked to worker %s. Reset to pending.',
                              job.uuid, self.uuid, job.worker_uuid)
                with session_hdl.session() as session:
                    job.set_pending()
                    self.job_storage_class(session).store(job)
                return

            if job.eta and job.eta > datetime.now():
                # The queue is sorted by 'eta' date first
                # so if we dequeued a job expected to be run in
                # the future, we have no jobs to do right now!
                self.queue.enqueue(job)
                # Wait some time just to avoid to loop over
                # the same 'future' jobs
                _logger.debug('Wait %s seconds because the delayed '
                              'jobs have been reached',
                              WAIT_WHEN_ONLY_AFTER_JOBS)
                time.sleep(WAIT_WHEN_ONLY_AFTER_JOBS)
                return

            with session_hdl.session() as session:
                job.set_started()
                self.job_storage_class(session).store(job)

            _logger.debug('%s started', job)
            with session_hdl.session() as session:
                job.perform(session)
            _logger.debug('%s done', job)

            with session_hdl.session() as session:
                job.set_done()
                self.job_storage_class(session).store(job)

        except NothingToDoJob as err:
            if unicode(err):
                msg = unicode(err)
            else:
                msg = None
            job.cancel(msg)
            with session_hdl.session() as session:
                self.job_storage_class(session).store(job)

        except RetryableJobError as err:
            # delay the job later, requeue
            retry_postpone(job, unicode(err))
            _logger.debug('%s postponed', job)

        except OperationalError as err:
            # Automatically retry the typical transaction serialization errors
            if err.pgcode not in PG_CONCURRENCY_ERRORS_TO_RETRY:
                raise
            retry_postpone(job, unicode(err), seconds=PG_RETRY)
            _logger.debug('%s OperionalError, postponed', job)

        except (FailedJobError, Exception):
            buff = StringIO()
            traceback.print_exc(file=buff)
            _logger.error(buff.getvalue())

            job.set_failed(exc_info=buff.getvalue())
            with session_hdl.session() as session:
                self.job_storage_class(session).store(job)
            raise

    def _load_job(self, session, job_uuid):
        """ Reload a job from the backend """
        try:
            job = self.job_storage_class(session).load(job_uuid)
        except NoSuchJobError:
            # just skip it
            job = None
        except NotReadableJobError:
            _logger.exception('Could not read job: %s', job_uuid)
            raise
        return job

    def run(self):
        """ Worker's main loop

        Check if it still exists in the ``watcher``. When it does no
        longer exist, it break the loop so the thread stops properly.

        Wait for jobs and execute them sequentially.
        """
        while 1:
            # check if the worker has to exit (db destroyed, connector
            # uninstalled)
            if self.watcher.worker_lost(self):
                break
            job = self.queue.dequeue()
            try:
                self.run_job(job)
            except:
                continue

    def enqueue_job_uuid(self, job_uuid):
        """ Enqueue a job:

        It will be executed by the worker as soon as possible (according
        to the job's priority
        """
        session_hdl = ConnectorSessionHandler(self.db_name,
                                              openerp.SUPERUSER_ID)
        with session_hdl.session() as session:
            job = self._load_job(session, job_uuid)
            if job is None:
                # skip a deleted job
                return
            job.set_enqueued(self)
            self.job_storage_class(session).store(job)
        # the change of state should be commited before
        # the enqueue otherwise we may have concurrent updates
        # if the job is started directly
        self.queue.enqueue(job)
        _logger.debug('%s enqueued in %s', job, self)


class WorkerWatcher(threading.Thread):
    """ Keep a sight on the workers and signal their aliveness.

    A `WorkerWatcher` is shared between databases, so only 1 instance is
    necessary to check the aliveness of the workers for every database.
    """

    def __init__(self):
        super(WorkerWatcher, self).__init__()
        self._workers = {}

    def _new(self, db_name):
        """ Create a new worker for the database """
        if db_name in self._workers:
            raise Exception('Database %s already has a worker (%s)' %
                            (db_name, self._workers[db_name].uuid))
        worker = Worker(db_name, self)
        self._workers[db_name] = worker
        worker.daemon = True
        worker.start()

    def _delete(self, db_name):
        """ Delete a worker associated with a database """
        if db_name in self._workers:
            worker_uuid = self._workers[db_name].uuid
            # the worker will exit (it checks ``worker_lost()``)
            del self._workers[db_name]

    def worker_for_db(self, db_name):
        return self._workers.get(db_name)

    def worker_lost(self, worker):
        """ Indicate if a worker is no longer referenced by the watcher.

        Used by the worker threads to know if they have to exit.
        """
        return worker not in self._workers.itervalues()

    @staticmethod
    def available_db_names():
        """ Returns the databases for the server having
        the connector module installed.

        Available means that they can be used by a `Worker`.

        :return: database names
        :rtype: list
        """
        if config['db_name']:
            db_names = config['db_name'].split(',')
        else:
            services = openerp.netsvc.ExportService._services
            if services.get('db'):
                db_names = services['db'].exp_list(True)
            else:
                db_names = []
        available_db_names = []
        for db_name in db_names:
            session_hdl = ConnectorSessionHandler(db_name,
                                                  openerp.SUPERUSER_ID)
            with session_hdl.session() as session:
                cr = session.cr
                try:
                    cr.execute("SELECT 1 FROM ir_module_module "
                               "WHERE name = %s "
                               "AND state = %s", ('connector', 'installed'),
                               log_exceptions=False)
                except ProgrammingError as err:
                    if unicode(err).startswith('relation "ir_module_module" does not exist'):
                        _logger.debug('Database %s is not an OpenERP database,'
                                      ' connector worker not started', db_name)
                    else:
                        raise
                else:
                    if cr.fetchone():
                        available_db_names.append(db_name)
        return available_db_names

    def _update_workers(self):
        """ Refresh the list of workers according to the available
        databases and registries.

        A new database can be available, so we need to create a new
        `Worker` or a database could have been dropped, so we have to
        discard the Worker.
        """
        db_names = self.available_db_names()
        # deleted db or connector uninstalled: remove the workers
        for db_name in set(self._workers) - set(db_names):
            self._delete(db_name)

        for db_name in db_names:
            if db_name not in self._workers:
                self._new(db_name)

    def run(self):
        """ `WorkerWatcher`'s main loop """
        while 1:
            self._update_workers()
            for db_name, worker in self._workers.items():
                self.check_alive(db_name, worker)
            time.sleep(WAIT_CHECK_WORKER_ALIVE)

    def check_alive(self, db_name, worker):
        """ Check if the the worker is still alive and notify
        its aliveness.
        Check if the other workers are still alive, if they are
        dead, remove them from the worker's pool.
        """
        session_hdl = ConnectorSessionHandler(db_name,
                                              openerp.SUPERUSER_ID)
        with session_hdl.session() as session:
            if worker.is_alive():
                self._notify_alive(session, worker)
                session.commit()
            self._purge_dead_workers(session)
            session.commit()

    def _notify_alive(self, session, worker):
        _logger.debug('Worker %s is alive on process %s',
                      worker.uuid, os.getpid())
        dbworker_obj = session.pool.get('queue.worker')
        dbworker_obj._notify_alive(session.cr,
                                   session.uid,
                                   worker,
                                   context=session.context)

    def _purge_dead_workers(self, session):
        dbworker_obj = session.pool.get('queue.worker')
        dbworker_obj._purge_dead_workers(session.cr,
                                         session.uid,
                                         context=session.context)


watcher = WorkerWatcher()


def start_service():
    """ Start the watcher """
    watcher.daemon = True
    watcher.start()

# We have to launch the Jobs Workers only if:
# 1. OpenERP is used in standalone mode (monoprocess)
# 2. Or it is used in multiprocess (with option ``--workers``)
#    but the current process is a Connector Worker
#    (launched with the ``openerp-connector-worker`` script).
if (not getattr(openerp, 'multi_process', False) or
        getattr(openerp, 'worker_connector', False)):
    start_service()
