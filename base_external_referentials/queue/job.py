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

import logging
import inspect
import uuid
import importlib
from datetime import datetime, timedelta, MINYEAR
from pickle import loads, dumps, UnpicklingError

from openerp import SUPERUSER_ID
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT

from ..exception import NotReadableJobError, NoSuchJobError


PENDING = 'pending'
ENQUEUED = 'enqueued'
DONE = 'done'
STARTED = 'started'
FAILED = 'failed'

STATES = [(PENDING, 'Pending'),
          (ENQUEUED, 'Queued'),
          (DONE, 'Done'),
          (STARTED, 'Started'),
          (FAILED, 'Failed')]

DEFAULT_PRIORITY = 10  # used by the PriorityQueue to sort the jobs

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

    def load(self, job_id):
        """ Read the job's data from the storage """
        raise NotImplementedError

    def exists(self, job_id):
        """Returns if a job still exists in the storage."""
        raise NotImplementedError


class OpenERPJobStorage(JobStorage):
    """ Store a job on OpenERP """

    _storage_model_name = 'jobs.storage'

    def __init__(self, session):
        super(OpenERPJobStorage, self).__init__()
        self.session = session
        self.storage_model = self.session.pool.get(self._storage_model_name)
        assert self.storage_model is not None, (
                "Model %s not found" % self._storage_model_name)

    def enqueue(self, func, args=None, kwargs=None,
                priority=None, only_after=None):
        job = Job(func=func, args=args, kwargs=kwargs,
                  priority=priority, only_after=only_after)
        job.user_id = self.session.uid
        self.store(job)

    def enqueue_resolve_args(self, func, *args, **kwargs):
        """Create a Job and enqueue it in the queue"""
        priority = kwargs.pop('priority', None)
        only_after = kwargs.pop('only_after', None)

        return self.enqueue(func, args=args, kwargs=kwargs,
                            priority=priority,
                            only_after=only_after)

    def exists(self, job_id):
        """Returns if a job still exists in the storage."""
        return bool(self._openerp_id(job_id))

    def _openerp_id(self, job_id):
        openerp_id = None
        job_ids = self.storage_model.search(
                self.session.cr,
                SUPERUSER_ID,
                [('uuid', '=', job_id)],
                context=self.session.context,
                limit=1)
        if job_ids:
            openerp_id = job_ids[0]
        return openerp_id

    def openerp_id(self, job):
        return self._openerp_id(job.id)

    def store(self, job):
        """ Store the Job """
        vals = dict(uuid=job.id,
                    state=job.state,
                    name=job.description,
                    func_string=job.func_string)

        vals['func'] = dumps((job.func_name,
                              job.args,
                              job.kwargs))

        if job.date_created:
            vals['date_created'] = job.date_created.strftime(
                    DEFAULT_SERVER_DATETIME_FORMAT)
        if job.date_enqueued:
            vals['date_enqueued'] = job.date_enqueued.strftime(
                    DEFAULT_SERVER_DATETIME_FORMAT)
        if job.date_started:
            vals['date_started'] = job.date_started.strftime(
                    DEFAULT_SERVER_DATETIME_FORMAT)
        if job.date_done:
            vals['date_done'] = job.date_done.strftime(
                    DEFAULT_SERVER_DATETIME_FORMAT)
        if job.only_after:
            vals['only_after'] = job.only_after.strftime(
                    DEFAULT_SERVER_DATETIME_FORMAT)

        if job.exc_info is not None:
            vals['exc_info'] = job.exc_info

        if job.result is not None:
            vals['result'] = unicode(job.result)

        vals['user_id'] = job.user_id

        if self.exists(job):
            self.storage_model.write(
                    self.session.cr,
                    self.session.uid,
                    self.openerp_id,
                    vals,
                    self.session.context)
        else:
            self.storage_model.create(
                    self.session.cr,
                    self.session.uid,
                    vals,
                    self.session.context)

    def load(self, job_id):
        """ Read a job from the Database"""
        if not self.exists(job_id):
            raise NoSuchJobError(
                    '%s does no longer exist in the storage.' % job_id)
        stored = self.storage_model.browse(self.session.cr,
                                           self.session.uid,
                                           self._openerp_id(job_id),
                                           context=self.session.context)

        func = unpickle(str(stored.func))  # openerp stores them as unicode...

        (func_name,
         args,
         kwargs) = func

        only_after = None
        if stored.only_after:
            only_after = datetime.strptime(stored.only_after,
                                           DEFAULT_SERVER_DATETIME_FORMAT)

        job = Job(func=func_name, args=args, kwargs=kwargs,
                  priority=stored.priority, only_after=only_after,
                  job_id=stored.uuid)

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
        job.user_id = stored.user_id
        return job


class Job(object):
    """ A Job is a task to execute """

    def __init__(self, func=None,
                 args=None, kwargs=None, priority=None,
                 only_after=None, job_id=None):
        """ Create a Job

        :param func: function to execute
        :type func: function
        :param args: arguments for func
        :type args: tuple
        :param kwargs: keyworkd arguments for func
        :type kwargs: dict
        :param priority: priority of the job, the smaller is the higher priority
        :type priority: int
        :param only_after: the job can be executed only after this datetime
                           (or now + timedelta)
        :type only_after: datetime or timedelta
        :param job_id: UUID of the job
        """
        if args is None:
            args = ()
        assert isinstance(args, tuple), "%s: args are not a tuple" % args
        if kwargs is None:
            kwargs = {}

        assert isinstance(kwargs, dict), "%s: kwargs are not a dict" % kwargs
        assert not func is None, "func is required"

        self.state = PENDING

        self._id = job_id

        self.func_name = None
        if func:
            if inspect.ismethod(func):
                raise NotImplementedError('Jobs on instances methods are not supported')
            elif inspect.isfunction(func):
                self.func_name = '%s.%s' % (func.__module__, func.__name__)
            elif isinstance(func, basestring):
                self.func_name = func
            else:
                raise TypeError('%s is not a valid function for a job' % func)

        self.args = args
        self.kwargs = kwargs

        if isinstance(only_after, timedelta):
            self.only_after = datetime.now() + only_after
        else:
            self.only_after = only_after
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

    def __cmp__(self, other):
        self_after = self.only_after or datetime(MINYEAR, 1, 1)
        other_after = other.only_after or datetime(MINYEAR, 1, 1)
        return cmp((self_after, self.priority),
                   (other_after, other.priority))

    def perform(self, session):
        """ Execute a job.

        The job is executed with the user which has initiated it.

        :param session: session execute the job
        :type session: ConnectorSession
        """
        with session.transaction().change_user(self.user_id):
            self.result = self.func(session, *self.args, **self.kwargs)
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
    def id(self):
        """Job ID, this is an UUID """
        if self._id is None:
            self._id = unicode(uuid.uuid4())
        return self._id

    @property
    def func(self):
        func_name = self.func_name
        if func_name is None:
            return None

        module_name, func_name = func_name.rsplit('.', 1)
        module = importlib.import_module(module_name)
        return getattr(module, func_name)

    def set_state(self, state, result=None, exc_info=None):
        """Change the state of the job."""
        self.state = state

        if state == ENQUEUED:
            self.date_enqueued = datetime.now()
        if state == STARTED:
            self.date_started = datetime.now()
        if state == DONE:
            self.date_done = datetime.now()

        if result is not None:
            self.result = result

        if exc_info is not None:
            self.exc_info = exc_info

    def __repr__(self):
        return '<Job %s, priority:%d>' % (self.id, self.priority)


def job(func):
    """ Decorator for jobs.

    Add a ``delay`` attribute on the decorated function.

    When ``delay`` is called, the function is transformed to a job and
    stored in the OpenERP queue.job model. The arguments and keyword
    arguments given in ``delay`` will be the arguments used by the
    decorated function when it is executed.
    """
    def delay(session, *args, **kwargs):
        OpenERPJobStorage.enqueue_resolve_args(session, func, *args, **kwargs)
    func.delay = delay
    return func


