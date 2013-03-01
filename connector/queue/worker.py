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
from datetime import datetime, timedelta
from StringIO import StringIO

import openerp
import openerp.modules.registry as registry_module
from .queue import JobsQueue
from ..session import ConnectorSessionHandler
from .job import (OpenERPJobStorage,
                  ENQUEUED,
                  STARTED,
                  FAILED,
                  DONE)
from ..exception import (NoSuchJobError,
                         NotReadableJobError,
                         RetryableJobError,
                         FailedJobError,
                         NothingToDoJob)

_logger = logging.getLogger(__name__)

WAIT_CHECK_WORKER_ALIVE = 5  # seconds TODO change to 30 seconds
WAIT_WHEN_ONLY_AFTER_JOBS = 10  # seconds
RETRY_JOB_TIMEDELTA = 60 * 10  # seconds


class Worker(threading.Thread):
    """ Post and retrieve jobs from the queue, execute them"""

    queue_class = JobsQueue
    job_storage_class = OpenERPJobStorage

    def __init__(self, db_name, watcher):
        super(Worker, self).__init__()
        self.queue = self.queue_class()
        self.db_name = db_name
        self.uuid = unicode(uuid.uuid4())
        self.watcher = watcher

    def run_job(self, job):
        """ Execute a job """
        session_hdl = ConnectorSessionHandler(self.db_name,
                                          openerp.SUPERUSER_ID)
        try:
            job = self._load_job(job)
            if job is None:
                return

            # if the job has been manually set to DONE
            # before its execution, stop
            if job.state == DONE:
                return

            if job.only_after and job.only_after > datetime.now():
                # The queue is sorted by 'only_after' date first
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
                job.set_state(STARTED)
                self.job_storage_class(session).store(job)

            _logger.debug('%s started', job)
            with session_hdl.session() as session:
                job.perform(session)
            _logger.debug('%s done', job)

            with session_hdl.session() as session:
                job.set_state(DONE)
                self.job_storage_class(session).store(job)

        except NothingToDoJob:
            job.cancel()
            with session_hdl.session() as session:
                self.job_storage_class(session).store(job)

        except RetryableJobError:
            # delay the job later
            job.only_after = timedelta(seconds=RETRY_JOB_TIMEDELTA)
            with session_hdl.session() as session:
                self.job_storage_class(session).store(job)

        except (FailedJobError, Exception):
            buff = StringIO()
            traceback.print_exc(file=buff)
            _logger.error(buff.getvalue())

            job.set_state(FAILED, exc_info=buff.getvalue())
            with session_hdl.session() as session:
                self.job_storage_class(session).store(job)
            raise

    def _load_job(self, job):
        """ Reload a job from the backend """
        session_hdl = ConnectorSessionHandler(self.db_name,
                                              openerp.SUPERUSER_ID)
        with session_hdl.session() as session:
            try:
                job = self.job_storage_class(session).load(job.uuid)
            except NoSuchJobError:
                # just skip it
                job = None
            except NotReadableJobError:
                _logger.exception('Could not read job: %s', job)
                raise
        return job

    def run(self):
        """ Worker's main loop

        Check if it still exists in the ``watcher``. When it does no
        longer exist, it break the loop so the thread stops properly.

        Wait for jobs and execute them sequentially.
        """
        while 1:
            # check if the worker has to exit
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
            try:
                job = self.job_storage_class(session).load(job_uuid)
            except NoSuchJobError:
                # just skip it
                return
            except NotReadableJobError:
                _logger.exception('Could not read job: %s', job_uuid)
                raise
            job.set_state(ENQUEUED)
            self.job_storage_class(session).store(job)
        # the change of state should be commited before
        # the enqueue otherwise we may have concurrent updates
        self.queue.enqueue(job)
        _logger.debug('%s enqueued in %s', job, self)


class WorkerWatcher(threading.Thread):
    """ Keep a sight on the workers and signal their aliveness.

    A `WorkerWatcher` is shared between databases, so only 1 instance is
    necessary to check the aliveness of the workers for every database.
    """

    def __init__(self):
        super(WorkerWatcher, self).__init__()
        self.workers = {}

    def new(self, db_name):
        """ Create a new worker for the database """
        if db_name in self.workers:
            raise Exception('Database %s already has a worker (%s)' %
                            (db_name, self.workers[db_name].uuid))
        worker = Worker(db_name, self)
        self.workers[db_name] = worker
        worker.daemon = True
        worker.start()

    def delete(self, db_name):
        """ Delete worker for the database """
        if db_name in self.workers:
            del self.workers[db_name]

    def worker_lost(self, worker):
        """ Indicate if a worker is no longer referenced by the watcher.

        Used by the worker threads to know they have to exit.
        """
        return worker not in self.workers.itervalues()

    @staticmethod
    def available_registries():
        """ Yield the registries which are available.

        Available means that they can be used by a `Worker`.

        :return: database name, registry
        :rtype: tuple
        """
        registries = registry_module.RegistryManager.registries
        for db_name, registry in registries.iteritems():
            if not 'connectors.installed' in registry.models:
                continue
            if not registry.ready:
                continue
            yield db_name, registry

    def _update_workers(self):
        """ Refresh the list of workers according to the available
        databases and registries.

        A new database can be available, so we need to create a new
        `Worker` or a database could have been dropped, so we have to
        discard the Worker.
        """
        for db_name, _registry in self.available_registries():
            if db_name not in self.workers:
                self.new(db_name)

        # XXX not necessary if we keep the monkey patch of
        # RegistryManager.delete
        all_db = registry_module.RegistryManager.registries.keys()
        for removed_db in set(self.workers) ^ set(all_db):
            self.delete(removed_db)

    def run(self):
        """ `WorkerWatcher`'s main loop """
        while 1:
            self._update_workers()
            for db_name, worker in self.workers.items():
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


registry_delete_original = registry_module.RegistryManager.delete
def delete(cls, db_name):
    """Delete the registry linked to a given database.  """
    watcher.delete(db_name)
    return registry_delete_original(db_name)
registry_module.RegistryManager.delete = classmethod(delete)


def start_service():
    """ Start the watcher """
    watcher.daemon = True
    watcher.start()

start_service()
