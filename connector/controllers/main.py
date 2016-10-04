import logging
import traceback
from cStringIO import StringIO

from psycopg2 import OperationalError

import odoo
from odoo import _, http, tools
from odoo.service.model import PG_CONCURRENCY_ERRORS_TO_RETRY

from ..queue.job import Job, ENQUEUED
from ..exception import (NoSuchJobError,
                         NotReadableJobError,
                         RetryableJobError,
                         FailedJobError,
                         NothingToDoJob)

_logger = logging.getLogger(__name__)

PG_RETRY = 5  # seconds


class RunJobController(http.Controller):

    def _load_job(self, env, job_uuid):
        """ Reload a job from the backend """
        try:
            job = Job.load(env, job_uuid)
        except NoSuchJobError:
            # just skip it
            job = None
        except NotReadableJobError:
            _logger.exception('Could not read job: %s', job_uuid)
            raise
        return job

    def _try_perform_job(self, env, job):
        """Try to perform the job."""

        # if the job has been manually set to DONE or PENDING,
        # or if something tries to run a job that is not enqueued
        # before its execution, stop
        if job.state != ENQUEUED:
            _logger.warning('job %s is in state %s '
                            'instead of enqueued in /runjob',
                            job.uuid, job.state)
            return

        # TODO: set_started should be done atomically with
        #       update queue_job set=state=started
        #       where state=enqueid and id=
        job.set_started()
        job.store()
        http.request.env.commit()

        _logger.debug('%s started', job)
        job.perform(env)
        job.set_done()
        job.store()
        http.request.env.commit()
        _logger.debug('%s done', job)

    @http.route('/connector/runjob', type='http', auth='none')
    def runjob(self, db, job_uuid, **kw):

        env = http.request.env(user=odoo.SUPERUSER_ID)

        def retry_postpone(job, message, seconds=None):
            job.postpone(result=message, seconds=seconds)
            job.set_pending(reset_retry=False)
            job.store()
            env.cr.commit()

        job = self._load_job(env, job_uuid)
        if job is None:
            return ""
        env.cr.commit()

        try:
            try:
                self._try_perform_job(env, job)
            except OperationalError as err:
                # Automatically retry the typical transaction serialization
                # errors
                if err.pgcode not in PG_CONCURRENCY_ERRORS_TO_RETRY:
                    raise

                retry_postpone(job, tools.ustr(err.pgerror, errors='replace'),
                               seconds=PG_RETRY)
                _logger.debug('%s OperationalError, postponed', job)

        except NothingToDoJob as err:
            if unicode(err):
                msg = unicode(err)
            else:
                msg = _('Job interrupted and set to Done: nothing to do.')
            job.set_done(msg)
            job.store()
            env.cr.commit()

        except RetryableJobError as err:
            # delay the job later, requeue
            retry_postpone(job, unicode(err), seconds=err.seconds)
            _logger.debug('%s postponed', job)

        except (FailedJobError, Exception):
            buff = StringIO()
            traceback.print_exc(file=buff)
            _logger.error(buff.getvalue())

            job.set_failed(exc_info=buff.getvalue())
            job.store()
            env.cr.commit()
            raise

        return ""
