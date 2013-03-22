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

import sys
import logging
import inspect
import uuid
from datetime import datetime, timedelta, MINYEAR
from pickle import loads, dumps, UnpicklingError

from openerp import SUPERUSER_ID
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp.tools.translate import _

from ..exception import (NotReadableJobError,
                         NoSuchJobError,
                         FailedJobError,
                         RetryableJobError)

__all__ = ['job']


PENDING = 'pending'
ENQUEUED = 'enqueued'
DONE = 'done'
STARTED = 'started'
FAILED = 'failed'

STATES = [(PENDING, 'Pending'),
          (ENQUEUED, 'Enqueued'),
          (STARTED, 'Started'),
          (DONE, 'Done'),
          (FAILED, 'Failed')]

DEFAULT_PRIORITY = 10  # used by the PriorityQueue to sort the jobs
DEFAULT_MAX_RETRIES = 3
RETRY_INTERVAL = 10 * 60  # seconds

_logger = logging.getLogger(__name__)


def unpickle(pickled):
    """ Unpickles a string and catch all types of errors it can throw,
    to raise only NotReadableJobError in case of error.

    OpenERP stores the text fields as 'utf-8', so we specify the encoding.

    `loads()` may raises many types of exceptions (AttributeError,
    IndexError, TypeError, KeyError, ...). They are all catched and
    raised as `NotReadableJobError`).
    """
    try:
        unpickled = loads(pickled.encode('utf-8'))
    except (StandardError, UnpicklingError):
        raise NotReadableJobError('Could not unpickle.', pickled)
    return unpickled


class JobStorage(object):
    """ Interface for the storage of jobs """

    def store(self, job):
        """ Store a job """
        raise NotImplementedError

    def load(self, job_uuid):
        """ Read the job's data from the storage """
        raise NotImplementedError

    def exists(self, job_uuid):
        """Returns if a job still exists in the storage."""
        raise NotImplementedError


class OpenERPJobStorage(JobStorage):
    """ Store a job on OpenERP """

    _storage_model_name = 'queue.job'

    def __init__(self, session):
        super(OpenERPJobStorage, self).__init__()
        self.session = session
        self.storage_model = self.session.pool.get(self._storage_model_name)
        assert self.storage_model is not None, (
                "Model %s not found" % self._storage_model_name)

    def enqueue(self, func, model_name=None, args=None, kwargs=None,
                priority=None, eta=None, max_retries=None):
        job = Job(func=func, model_name=model_name, args=args, kwargs=kwargs,
                  priority=priority, eta=eta, max_retries=max_retries)
        job.user_id = self.session.uid
        self.store(job)

    def enqueue_resolve_args(self, func, *args, **kwargs):
        """Create a Job and enqueue it in the queue"""
        priority = kwargs.pop('priority', None)
        eta = kwargs.pop('eta', None)
        model_name = kwargs.pop('model_name', None)
        max_retries = kwargs.pop('max_retries', None)

        return self.enqueue(func, model_name=model_name,
                            args=args, kwargs=kwargs,
                            priority=priority,
                            max_retries=max_retries,
                            eta=eta)

    def exists(self, job_uuid):
        """Returns if a job still exists in the storage."""
        return bool(self._openerp_id(job_uuid))

    def _openerp_id(self, job_uuid):
        openerp_id = None
        job_ids = self.storage_model.search(
                self.session.cr,
                SUPERUSER_ID,
                [('uuid', '=', job_uuid)],
                context=self.session.context,
                limit=1)
        if job_ids:
            openerp_id = job_ids[0]
        return openerp_id

    def openerp_id(self, job):
        return self._openerp_id(job.uuid)

    def store(self, job):
        """ Store the Job """
        vals = {'state': job.state,
                'priority': job.priority,
                'retry': job.retry,
                'max_retries': job.max_retries,
                'exc_info': job.exc_info,
                'user_id': job.user_id or self.session.uid,
                'result': unicode(job.result) if job.result else False,
                'date_enqueued': False,
                'date_started': False,
                'date_done': False,
                'eta': False,
                }

        if job.date_enqueued:
            vals['date_enqueued'] = job.date_enqueued.strftime(
                    DEFAULT_SERVER_DATETIME_FORMAT)
        if job.date_started:
            vals['date_started'] = job.date_started.strftime(
                    DEFAULT_SERVER_DATETIME_FORMAT)
        if job.date_done:
            vals['date_done'] = job.date_done.strftime(
                    DEFAULT_SERVER_DATETIME_FORMAT)
        if job.eta:
            vals['eta'] = job.eta.strftime(DEFAULT_SERVER_DATETIME_FORMAT)

        if job.state in (PENDING, DONE, FAILED):
            vals['worker_id'] = False
        if job.canceled:
            vals['active'] = False

        if self.exists(job.uuid):
            self.storage_model.write(
                    self.session.cr,
                    self.session.uid,
                    self.openerp_id(job),
                    vals,
                    self.session.context)
        else:
            date_created = job.date_created.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
            vals.update({'uuid': job.uuid,
                         'name': job.description,
                         'func_string': job.func_string,
                         'date_created': date_created,
                         'model_name': (job.model_name if job.model_name
                                        else False),
                         })

            vals['func'] = dumps((job.func_name,
                                  job.args,
                                  job.kwargs))

            self.storage_model.create(
                    self.session.cr,
                    self.session.uid,
                    vals,
                    self.session.context)

    def postpone(self, job):
        job.eta = timedelta(seconds=RETRY_INTERVAL)
        job.exc_info = None
        job.set_state(PENDING)
        self.store(job)

    def load(self, job_uuid):
        """ Read a job from the Database"""
        if not self.exists(job_uuid):
            raise NoSuchJobError(
                    '%s does no longer exist in the storage.' % job_uuid)
        stored = self.storage_model.browse(self.session.cr,
                                           self.session.uid,
                                           self._openerp_id(job_uuid),
                                           context=self.session.context)

        func = unpickle(str(stored.func))  # openerp stores them as unicode...

        (func_name, args, kwargs) = func

        eta = None
        if stored.eta:
            eta = datetime.strptime(stored.eta, DEFAULT_SERVER_DATETIME_FORMAT)

        job = Job(func=func_name, args=args, kwargs=kwargs,
                  priority=stored.priority, eta=eta, job_uuid=stored.uuid)

        if stored.date_created:
            job.date_created = datetime.strptime(
                    stored.date_created, DEFAULT_SERVER_DATETIME_FORMAT)

        if stored.date_enqueued:
            job.date_enqueued = datetime.strptime(
                    stored.date_enqueued, DEFAULT_SERVER_DATETIME_FORMAT)

        if stored.date_started:
            job.date_started = datetime.strptime(
                    stored.date_started, DEFAULT_SERVER_DATETIME_FORMAT)

        if stored.date_done:
            job.date_done = datetime.strptime(
                    stored.date_done, DEFAULT_SERVER_DATETIME_FORMAT)

        job.state = stored.state
        job.result = stored.result if stored.result else None
        job.exc_info = stored.exc_info if stored.exc_info else None
        job.user_id = stored.user_id.id if stored.user_id else None
        job.canceled = not stored.active
        job.model_name = stored.model_name if stored.model_name else None
        job.retry = stored.retry
        job.max_retries = stored.max_retries
        return job


class Job(object):
    """ A Job is a task to execute """

    def __init__(self, func=None, model_name=None,
                 args=None, kwargs=None, priority=None,
                 eta=None, job_uuid=None, max_retries=None):
        """ Create a Job

        :param func: function to execute
        :type func: function
        :param model_name: name of the model targetted by the job
        :type model_name: str
        :param args: arguments for func
        :type args: tuple
        :param kwargs: keyworkd arguments for func
        :type kwargs: dict
        :param priority: priority of the job, the smaller is the higher priority
        :type priority: int
        :param eta: the job can be executed only after this datetime
                           (or now + timedelta)
        :type eta: datetime or timedelta
        :param job_uuid: UUID of the job
        :param max_retries: maximum number of retries before giving up and set
            the job state to 'failed'. A value of 0 means infinite retries.
        """
        if args is None:
            args = ()
        assert isinstance(args, tuple), "%s: args are not a tuple" % args
        if kwargs is None:
            kwargs = {}

        assert isinstance(kwargs, dict), "%s: kwargs are not a dict" % kwargs
        assert not func is None, "func is required"

        self.state = PENDING

        self.retry = 0
        self.max_retries = max_retries or DEFAULT_MAX_RETRIES

        self._uuid = job_uuid

        self.func_name = None
        if func:
            if inspect.ismethod(func):
                raise NotImplementedError('Jobs on instances methods are '
                                          'not supported')
            elif inspect.isfunction(func):
                self.func_name = '%s.%s' % (func.__module__, func.__name__)
            elif isinstance(func, basestring):
                self.func_name = func
            else:
                raise TypeError('%s is not a valid function for a job' % func)

        self.model_name = model_name
        # the model name is by convention the second argument of the job
        if self.model_name:
            args = tuple([self.model_name] + list(args))
        self.args = args
        self.kwargs = kwargs

        self.priority = priority
        if self.priority is None:
            self.priority = DEFAULT_PRIORITY

        self.date_created = datetime.now()
        self.date_enqueued = None
        self.date_started = None
        self.date_done = None

        self.result = None
        self.exc_info = None

        self.user_id = None
        self.eta = eta
        self.canceled = False

    def __cmp__(self, other):
        if not isinstance(other, Job):
            raise TypeError("Job.__cmp__(self, other) requires other to be "
                            "a 'Job', not a '%s'" % type(other))
        self_eta = self.eta or datetime(MINYEAR, 1, 1)
        other_eta = other.eta or datetime(MINYEAR, 1, 1)
        return cmp((self_eta, self.priority, self.date_created),
                   (other_eta, other.priority, other.date_created))

    def perform(self, session):
        """ Execute a job.

        The job is executed with the user which has initiated it.

        :param session: session to execute the job
        :type session: ConnectorSession
        """
        assert not self.canceled, "Canceled job"
        with session.change_user(self.user_id):
            self.retry += 1
            try:
                self.result = self.func(session, *self.args, **self.kwargs)
            except RetryableJobError:
                if not self.max_retries:  # infinite retries
                    raise
                elif self.retry >= self.max_retries:
                    type, value, traceback = sys.exc_info()
                    # change the exception type but keep the original
                    # traceback and message:
                    # http://blog.ianbicking.org/2007/09/12/re-raising-exceptions/
                    new_exc = FailedJobError("Max. retries (%d) reached: %s" %
                                             (self.max_retries, value or type))
                    raise new_exc.__class__, new_exc, traceback
                raise
        return self.result

    @property
    def func_string(self):
        if self.func_name is None:
            return None
        args = [repr(arg) for arg in self.args]
        kwargs = ['%s=%r' % (key, val) for key, val
                  in self.kwargs.iteritems()]
        return '%s(%s)' % (self.func_name, ', '.join(args + kwargs))

    @property
    def description(self):
        return self.func.__doc__ or 'Function %s' % self.func.__name__

    @property
    def uuid(self):
        """Job ID, this is an UUID """
        if self._uuid is None:
            self._uuid = unicode(uuid.uuid4())
        return self._uuid

    @property
    def func(self):
        func_name = self.func_name
        if func_name is None:
            return None

        module_name, func_name = func_name.rsplit('.', 1)
        __import__(module_name)
        module = sys.modules[module_name]
        return getattr(module, func_name)

    @property
    def eta(self):
        return self._eta

    @eta.setter
    def eta(self, value):
        if not value:
            self._eta = None
        elif isinstance(value, timedelta):
            self._eta = datetime.now() + value
        elif isinstance(value, datetime):
            self._eta = value
        elif instance(value, int):
            self._eta = datetime.now() + timedelta(seconds=value)
        else:
            raise ValueError("%s is not a valid type for eta, "
                             " it must be an 'int',  a 'timedelta' "
                             "or a 'datetime'" % type(value))

    def set_state(self, state, result=None, exc_info=None):
        """Change the state of the job."""
        self.state = state

        if state == PENDING:
            self.date_enqueued = None
            self.date_started = None

        if state == ENQUEUED:
            self.date_enqueued = datetime.now()
            self.date_started = None
        if state == STARTED:
            self.date_started = datetime.now()
        if state == DONE:
            self.exc_info = None
            self.date_done = datetime.now()

        if result is not None:
            self.result = result

        if exc_info is not None:
            self.exc_info = exc_info

    def __repr__(self):
        return '<Job %s, priority:%d>' % (self.uuid, self.priority)

    def cancel(self, msg=None):
        self.canceled = True
        result = msg if msg is not None else _('Nothing to do')
        self.set_state(DONE, result=result)


def job(func):
    """ Decorator for jobs.

    Add a ``delay`` attribute on the decorated function.

    When ``delay`` is called, the function is transformed to a job and
    stored in the OpenERP queue.job model. The arguments and keyword
    arguments given in ``delay`` will be the arguments used by the
    decorated function when it is executed.
    """
    def delay(session, model_name, *args, **kwargs):
        OpenERPJobStorage(session).enqueue_resolve_args(func,
                                                        model_name=model_name,
                                                        *args, **kwargs)
    func.delay = delay
    return func
