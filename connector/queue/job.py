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

import inspect
import functools
import logging
import uuid
import sys
from datetime import datetime, timedelta, MINYEAR
from pickle import loads, dumps, UnpicklingError

from openerp import SUPERUSER_ID
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp.tools.translate import _

from ..exception import (NotReadableJobError,
                         NoSuchJobError,
                         FailedJobError,
                         RetryableJobError)

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
DEFAULT_MAX_RETRIES = 5
RETRY_INTERVAL = 10 * 60  # seconds

_logger = logging.getLogger(__name__)


def _unpickle(pickled):
    """ Unpickles a string and catch all types of errors it can throw,
    to raise only NotReadableJobError in case of error.

    OpenERP stores the text fields as 'utf-8', so we specify the encoding.

    `loads()` may raises many types of exceptions (AttributeError,
    IndexError, TypeError, KeyError, ...). They are all catched and
    raised as `NotReadableJobError`).
    """
    try:
        unpickled = loads(pickled)
    except (StandardError, UnpicklingError):
        raise NotReadableJobError('Could not unpickle.', pickled)
    return unpickled


class JobStorage(object):
    """ Interface for the storage of jobs """

    def store(self, job_):
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

    _job_model_name = 'queue.job'
    _worker_model_name = 'queue.worker'

    def __init__(self, session):
        super(OpenERPJobStorage, self).__init__()
        self.session = session
        self.job_model = self.session.pool.get(self._job_model_name)
        self.worker_model = self.session.pool.get(self._worker_model_name)
        assert self.job_model is not None, (
            "Model %s not found" % self._job_model_name)

    def enqueue(self, func, model_name=None, args=None, kwargs=None,
                priority=None, eta=None, max_retries=None, description=None):
        """Create a Job and enqueue it in the queue. Return the job uuid.

        This expects the arguments specific to the job to be already extracted
        from the ones to pass to the job function.

        """
        new_job = Job(func=func, model_name=model_name, args=args,
                      kwargs=kwargs, priority=priority, eta=eta,
                      max_retries=max_retries, description=description)
        new_job.user_id = self.session.uid
        if 'company_id' in self.session.context:
            company_id = self.session.context['company_id']
        else:
            company_obj = self.session.pool['res.company']
            company_id = company_obj._company_default_get(
                self.session.cr,
                new_job.user_id,
                object='queue.job',
                field='company_id',
                context=self.session.context)
        new_job.company_id = company_id
        self.store(new_job)
        return new_job.uuid

    def enqueue_resolve_args(self, func, *args, **kwargs):
        """Create a Job and enqueue it in the queue. Return the job uuid."""
        priority = kwargs.pop('priority', None)
        eta = kwargs.pop('eta', None)
        model_name = kwargs.pop('model_name', None)
        max_retries = kwargs.pop('max_retries', None)
        description = kwargs.pop('description', None)

        return self.enqueue(func, model_name=model_name,
                            args=args, kwargs=kwargs,
                            priority=priority,
                            max_retries=max_retries,
                            eta=eta,
                            description=description)

    def exists(self, job_uuid):
        """Returns if a job still exists in the storage."""
        return bool(self._openerp_id(job_uuid))

    def _openerp_id(self, job_uuid):
        openerp_id = None
        job_ids = self.job_model.search(self.session.cr,
                                        SUPERUSER_ID,
                                        [('uuid', '=', job_uuid)],
                                        context=self.session.context,
                                        limit=1)
        if job_ids:
            openerp_id = job_ids[0]
        return openerp_id

    def openerp_id(self, job_):
        return self._openerp_id(job_.uuid)

    def _worker_id(self, worker_uuid):
        openerp_id = None
        worker_ids = self.worker_model.search(self.session.cr,
                                              SUPERUSER_ID,
                                              [('uuid', '=', worker_uuid)],
                                              context=self.session.context,
                                              limit=1)
        if worker_ids:
            openerp_id = worker_ids[0]
        return openerp_id

    def store(self, job_):
        """ Store the Job """
        vals = {'state': job_.state,
                'priority': job_.priority,
                'retry': job_.retry,
                'max_retries': job_.max_retries,
                'exc_info': job_.exc_info,
                'user_id': job_.user_id or self.session.uid,
                'company_id': job_.company_id,
                'result': unicode(job_.result) if job_.result else False,
                'date_enqueued': False,
                'date_started': False,
                'date_done': False,
                'eta': False,
                }

        if job_.date_enqueued:
            vals['date_enqueued'] = job_.date_enqueued.strftime(
                DEFAULT_SERVER_DATETIME_FORMAT)
        if job_.date_started:
            vals['date_started'] = job_.date_started.strftime(
                DEFAULT_SERVER_DATETIME_FORMAT)
        if job_.date_done:
            vals['date_done'] = job_.date_done.strftime(
                DEFAULT_SERVER_DATETIME_FORMAT)
        if job_.eta:
            vals['eta'] = job_.eta.strftime(DEFAULT_SERVER_DATETIME_FORMAT)

        if job_.canceled:
            vals['active'] = False

        if job_.worker_uuid:
            vals['worker_id'] = self._worker_id(job_.worker_uuid)
        else:
            vals['worker_id'] = False

        if self.exists(job_.uuid):
            self.job_model.write(self.session.cr,
                                 self.session.uid,
                                 self.openerp_id(job_),
                                 vals,
                                 self.session.context)
        else:
            fmt = DEFAULT_SERVER_DATETIME_FORMAT
            date_created = job_.date_created.strftime(fmt)
            vals.update({'uuid': job_.uuid,
                         'name': job_.description,
                         'func_string': job_.func_string,
                         'date_created': date_created,
                         'model_name': (job_.model_name if job_.model_name
                                        else False),
                         })

            vals['func'] = dumps((job_.func_name,
                                  job_.args,
                                  job_.kwargs))

            self.job_model.create(self.session.cr,
                                  SUPERUSER_ID,
                                  vals,
                                  self.session.context)

    def load(self, job_uuid):
        """ Read a job from the Database"""
        if not self.exists(job_uuid):
            raise NoSuchJobError(
                '%s does no longer exist in the storage.' % job_uuid)
        stored = self.job_model.browse(self.session.cr,
                                       self.session.uid,
                                       self._openerp_id(job_uuid),
                                       context=self.session.context)

        func = _unpickle(stored.func)

        (func_name, args, kwargs) = func

        eta = None
        if stored.eta:
            eta = datetime.strptime(stored.eta, DEFAULT_SERVER_DATETIME_FORMAT)

        job_ = Job(func=func_name, args=args, kwargs=kwargs,
                   priority=stored.priority, eta=eta,
                   job_uuid=stored.uuid, description=stored.name)

        if stored.date_created:
            job_.date_created = datetime.strptime(
                stored.date_created, DEFAULT_SERVER_DATETIME_FORMAT)

        if stored.date_enqueued:
            job_.date_enqueued = datetime.strptime(
                stored.date_enqueued, DEFAULT_SERVER_DATETIME_FORMAT)

        if stored.date_started:
            job_.date_started = datetime.strptime(
                stored.date_started, DEFAULT_SERVER_DATETIME_FORMAT)

        if stored.date_done:
            job_.date_done = datetime.strptime(
                stored.date_done, DEFAULT_SERVER_DATETIME_FORMAT)

        job_.state = stored.state
        job_.result = stored.result if stored.result else None
        job_.exc_info = stored.exc_info if stored.exc_info else None
        job_.user_id = stored.user_id.id if stored.user_id else None
        job_.canceled = not stored.active
        job_.model_name = stored.model_name if stored.model_name else None
        job_.retry = stored.retry
        job_.max_retries = stored.max_retries
        if stored.worker_id:
            job_.worker_uuid = stored.worker_id.uuid
        if stored.company_id:
            job_.company_id = stored.company_id.id
        return job_


class Job(object):
    """ A Job is a task to execute.

    .. attribute:: uuid

        Id (UUID) of the job.

    .. attribute:: worker_uuid

        When the job is enqueued, UUID of the worker.

    .. attribute:: state

        State of the job, can pending, enqueued, started, done or failed.
        The start state is pending and the final state is done.

    .. attribute:: retry

        The current try, starts at 0 and each time the job is executed,
        it increases by 1.

    .. attribute:: max_retries

        The maximum number of retries allowed before the job is
        considered as failed.

    .. attribute:: func_name

        Name of the function (in the form module.function_name).

    .. attribute:: args

        Arguments passed to the function when executed.

    .. attribute:: kwargs

        Keyword arguments passed to the function when executed.

    .. attribute:: func_string

        Full string representing the function to be executed,
        ie. module.function(args, kwargs)

    .. attribute:: description

        Human description of the job.

    .. attribute:: func

        The python function itself.

    .. attribute:: model_name

        OpenERP model on which the job will run.

    .. attribute:: priority

        Priority of the job, 0 being the higher priority.

    .. attribute:: date_created

        Date and time when the job was created.

    .. attribute:: date_enqueued

        Date and time when the job was enqueued.

    .. attribute:: date_started

        Date and time when the job was started.

    .. attribute:: date_done

        Date and time when the job was done.

    .. attribute:: result

        A description of the result (for humans).

    .. attribute:: exc_info

        Exception information (traceback) when the job failed.

    .. attribute:: user_id

        OpenERP user id which created the job

    .. attribute:: eta

        Estimated Time of Arrival of the job. It will not be executed
        before this date/time.

    .. attribute:: canceled

        True if the job has been canceled.

    """

    def __init__(self, func=None, model_name=None,
                 args=None, kwargs=None, priority=None,
                 eta=None, job_uuid=None, max_retries=None, description=None):
        """ Create a Job

        :param func: function to execute
        :type func: function
        :param model_name: name of the model targetted by the job
        :type model_name: str
        :param args: arguments for func
        :type args: tuple
        :param kwargs: keyworkd arguments for func
        :type kwargs: dict
        :param priority: priority of the job,
                         the smaller is the higher priority
        :type priority: int
        :param eta: the job can be executed only after this datetime
                           (or now + timedelta)
        :type eta: datetime or timedelta
        :param job_uuid: UUID of the job
        :param max_retries: maximum number of retries before giving up and set
            the job state to 'failed'. A value of 0 means infinite retries.
        :param description: human description of the job. If None, description
            is computed from the function doc or name
        """
        if args is None:
            args = ()
        assert isinstance(args, tuple), "%s: args are not a tuple" % args
        if kwargs is None:
            kwargs = {}

        assert isinstance(kwargs, dict), "%s: kwargs are not a dict" % kwargs
        assert func is not None, "func is required"

        self.state = PENDING

        self.retry = 0
        if max_retries is None:
            self.max_retries = DEFAULT_MAX_RETRIES
        else:
            self.max_retries = max_retries

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
        self._description = description
        self.date_enqueued = None
        self.date_started = None
        self.date_done = None

        self.result = None
        self.exc_info = None

        self.user_id = None
        self.company_id = None
        self._eta = None
        self.eta = eta
        self.canceled = False
        self.worker_uuid = None

    def __cmp__(self, other):
        if not isinstance(other, Job):
            raise TypeError("Job.__cmp__(self, other) requires other to be "
                            "a 'Job', not a '%s'" % type(other))
        self_eta = self.eta or datetime(MINYEAR, 1, 1)
        other_eta = other.eta or datetime(MINYEAR, 1, 1)
        return cmp((self_eta, self.priority, self.date_created),
                   (other_eta, other.priority, other.date_created))

    def perform(self, session):
        """ Execute the job.

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
                    type_, value, traceback = sys.exc_info()
                    # change the exception type but keep the original
                    # traceback and message:
                    # http://blog.ianbicking.org/2007/09/12/re-raising-exceptions/
                    new_exc = FailedJobError("Max. retries (%d) reached: %s" %
                                             (self.max_retries, value or type_)
                                             )
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
        descr = (self._description or
                 self.func.__doc__ or
                 'Function %s' % self.func.__name__)
        return descr

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
        elif isinstance(value, int):
            self._eta = datetime.now() + timedelta(seconds=value)
        else:
            raise ValueError("%s is not a valid type for eta, "
                             " it must be an 'int', a 'timedelta' "
                             "or a 'datetime'" % type(value))

    def set_pending(self, result=None):
        self.state = PENDING
        self.date_enqueued = None
        self.date_started = None
        self.worker_uuid = None
        self.retry = 0
        if result is not None:
            self.result = result

    def set_enqueued(self, worker):
        self.state = ENQUEUED
        self.date_enqueued = datetime.now()
        self.date_started = None
        self.worker_uuid = worker.uuid

    def set_started(self):
        self.state = STARTED
        self.date_started = datetime.now()

    def set_done(self, result=None):
        self.state = DONE
        self.exc_info = None
        self.date_done = datetime.now()
        self.worker_uuid = None
        if result is not None:
            self.result = result

    def set_failed(self, exc_info=None):
        self.state = FAILED
        self.worker_uuid = None
        if exc_info is not None:
            self.exc_info = exc_info

    def __repr__(self):
        return '<Job %s, priority:%d>' % (self.uuid, self.priority)

    def cancel(self, msg=None):
        self.canceled = True
        result = msg if msg is not None else _('Canceled. Nothing to do.')
        self.set_done(result=result)

    def postpone(self, result=None, seconds=None):
        """ Write an estimated time arrival to n seconds
        later than now. Used when an retryable exception
        want to retry a job later. """
        if seconds is None:
            seconds = RETRY_INTERVAL
        self.eta = timedelta(seconds=seconds)
        self.exc_info = None
        if result is not None:
            self.result = result

    def related_action(self, session):
        if not hasattr(self.func, 'related_action'):
            return None
        return self.func.related_action(session, self)


def job(func):
    """ Decorator for jobs.

   Add a ``delay`` attribute on the decorated function.

   When ``delay`` is called, the function is transformed to a job and
   stored in the OpenERP queue.job model. The arguments and keyword
   arguments given in ``delay`` will be the arguments used by the
   decorated function when it is executed.

   The ``delay()`` function of a job takes the following arguments:

   session
     Current :py:class:`~openerp.addons.connector.session.ConnectorSession`

   model_name
     name of the model on which the job has something to do

   *args and **kargs
     Arguments and keyword arguments which will be given to the called
     function once the job is executed. They should be ``pickle-able``.

     There is 4 special and reserved keyword arguments that you can use:

     * priority: priority of the job, the smaller is the higher priority.
                 Default is 10.
     * max_retries: maximum number of retries before giving up and set
                    the job state to 'failed'. A value of 0 means
                    infinite retries. Default is 5.
     * eta: the job can be executed only after this datetime
            (or now + timedelta if a timedelta or integer is given)

     * description : a human description of the job,
                     intended to discriminate job instances
                     (Default is the func.__doc__ or
                      'Function %s' % func.__name__)

    Example:

    .. code-block:: python

        @job
        def export_one_thing(session, model_name, one_thing):
            # work
            # export one_thing

        export_one_thing(session, 'a.model', the_thing_to_export)
        # => normal and synchronous function call

        export_one_thing.delay(session, 'a.model', the_thing_to_export)
        # => the job will be executed as soon as possible

        export_one_thing.delay(session, 'a.model', the_thing_to_export,
                               priority=30, eta=60*60*5)
        # => the job will be executed with a low priority and not before a
        # delay of 5 hours from now

    See also: :py:func:`related_action` a related action can be attached
    to a job

    """
    def delay(session, model_name, *args, **kwargs):
        """Enqueue the function. Return the uuid of the created job."""
        return OpenERPJobStorage(session).enqueue_resolve_args(
            func,
            model_name=model_name,
            *args,
            **kwargs)
    func.delay = delay
    return func


def related_action(action=lambda session, job: None, **kwargs):
    """ Attach a *Related Action* to a job.

    A *Related Action* will appear as a button on the OpenERP view.
    The button will execute the action, usually it will open the
    form view of the record related to the job.

    The ``action`` must be a callable that responds to arguments::

        session, job, **kwargs

    Example usage:

    .. code-block:: python

        def related_action_partner(session, job):
            model = job.args[0]
            partner_id = job.args[1]
            # eventually get the real ID if partner_id is a binding ID
            action = {
                'name': _("Partner"),
                'type': 'ir.actions.act_window',
                'res_model': model,
                'view_type': 'form',
                'view_mode': 'form',
                'res_id': partner_id,
            }
            return action

        @job
        @related_action(action=related_action_partner)
        def export_partner(session, model_name, partner_id):
            # ...

    The kwargs are transmitted to the action:

    .. code-block:: python

        def related_action_product(session, job, extra_arg=1):
            assert extra_arg == 2
            model = job.args[0]
            product_id = job.args[1]

        @job
        @related_action(action=related_action_product, extra_arg=2)
        def export_product(session, model_name, product_id):
            # ...

    """
    def decorate(func):
        if kwargs:
            func.related_action = functools.partial(action, **kwargs)
        else:
            func.related_action = action
        return func
    return decorate
