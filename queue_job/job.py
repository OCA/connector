# -*- coding: utf-8 -*-
# Copyright 2013-2016 Camptocamp
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import inspect
import functools
import logging
import uuid
import sys
from datetime import datetime, timedelta

import odoo

from .exception import (NoSuchJobError,
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


class DelayableRecordset(object):
    """ Allow to delay a method for a recordset

    Usage::

        delayable = DelayableRecordset(recordset, priority=20)
        delayable.method(args, kwargs)

    ``method`` must be a method of the recordset's Model, decorated with
    :func:`~odoo.addons.queue_job.job.job`.

    The method call will be processed asynchronously in the job queue, with
    the passed arguments.


    """

    def __init__(self, recordset, priority=None, eta=None,
                 max_retries=None, description=None):
        self.recordset = recordset
        self.priority = priority
        self.eta = eta
        self.max_retries = max_retries
        self.description = description

    def __getattr__(self, name):
        if name in self.recordset:
            raise AttributeError(
                'only methods can be delayed (%s called on %s)' %
                (name, self.recordset)
            )
        recordset_method = getattr(self.recordset, name)
        if not getattr(recordset_method, 'delayable', None):
            raise AttributeError(
                'method %s on %s is not allowed to be delayed, '
                'it should be decorated with odoo.addons.queue_job.job.job' %
                (name, self.recordset)
            )

        def delay(*args, **kwargs):
            return Job.enqueue(recordset_method,
                               args=args,
                               kwargs=kwargs,
                               priority=self.priority,
                               max_retries=self.max_retries,
                               eta=self.eta,
                               description=self.description)
        return delay

    def __str__(self):
        return "DelayableRecordset(%s%s)" % (
            self.recordset._name,
            getattr(self.recordset, '_ids', "")
        )

    def __unicode__(self):
        return unicode(str(self))

    __repr__ = __str__


class Job(object):
    """ A Job is a task to execute.

    .. attribute:: uuid

        Id (UUID) of the job.

    .. attribute:: state

        State of the job, can pending, enqueued, started, done or failed.
        The start state is pending and the final state is done.

    .. attribute:: retry

        The current try, starts at 0 and each time the job is executed,
        it increases by 1.

    .. attribute:: max_retries

        The maximum number of retries allowed before the job is
        considered as failed.

    .. attribute:: args

        Arguments passed to the function when executed.

    .. attribute:: kwargs

        Keyword arguments passed to the function when executed.

    .. attribute:: description

        Human description of the job.

    .. attribute:: func

        The python function itself.

    .. attribute:: model_name

        Odoo model on which the job will run.

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

        Odoo user id which created the job

    .. attribute:: eta

        Estimated Time of Arrival of the job. It will not be executed
        before this date/time.

    .. attribute:: recordset

        Model recordset when we are on a delayed Model method

    """

    @classmethod
    def load(cls, env, job_uuid):
        """ Read a job from the Database"""
        stored = cls.db_record_from_uuid(env, job_uuid)
        if not stored:
            raise NoSuchJobError(
                'Job %s does no longer exist in the storage.' % job_uuid)

        args = stored.args
        kwargs = stored.kwargs
        method_name = stored.method_name

        model = env[stored.model_name]
        recordset = model.browse(stored.record_ids)
        method = getattr(recordset, method_name)

        dt_from_string = odoo.fields.Datetime.from_string
        eta = None
        if stored.eta:
            eta = dt_from_string(stored.eta)

        job_ = cls(method, args=args, kwargs=kwargs,
                   priority=stored.priority, eta=eta, job_uuid=stored.uuid,
                   description=stored.name)

        if stored.date_created:
            job_.date_created = dt_from_string(stored.date_created)

        if stored.date_enqueued:
            job_.date_enqueued = dt_from_string(stored.date_enqueued)

        if stored.date_started:
            job_.date_started = dt_from_string(stored.date_started)

        if stored.date_done:
            job_.date_done = dt_from_string(stored.date_done)

        job_.state = stored.state
        job_.result = stored.result if stored.result else None
        job_.exc_info = stored.exc_info if stored.exc_info else None
        job_.user_id = stored.user_id.id if stored.user_id else None
        job_.model_name = stored.model_name if stored.model_name else None
        job_.retry = stored.retry
        job_.max_retries = stored.max_retries
        if stored.company_id:
            job_.company_id = stored.company_id.id
        return job_

    @classmethod
    def enqueue(cls, func, args=None, kwargs=None,
                priority=None, eta=None, max_retries=None, description=None):
        """Create a Job and enqueue it in the queue. Return the job uuid.

        This expects the arguments specific to the job to be already extracted
        from the ones to pass to the job function.

        """
        new_job = cls(func=func, args=args,
                      kwargs=kwargs, priority=priority, eta=eta,
                      max_retries=max_retries, description=description)
        new_job.store()
        return new_job

    @staticmethod
    def db_record_from_uuid(env, job_uuid):
        model = env['queue.job'].sudo()
        record = model.search([('uuid', '=', job_uuid)], limit=1)
        return record.with_env(env)

    def __init__(self, func,
                 args=None, kwargs=None, priority=None,
                 eta=None, job_uuid=None, max_retries=None,
                 description=None):
        """ Create a Job

        :param func: function to execute
        :type func: function
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
        :param env: Odoo Environment
        :type env: :class:`odoo.api.Environment`
        """
        if args is None:
            args = ()
        if isinstance(args, list):
            args = tuple(args)
        assert isinstance(args, tuple), "%s: args are not a tuple" % args
        if kwargs is None:
            kwargs = {}

        assert isinstance(kwargs, dict), "%s: kwargs are not a dict" % kwargs

        if (not inspect.ismethod(func) or
                not isinstance(func.im_class, odoo.models.MetaModel)):
            raise TypeError("Job accepts only methods of Models")

        recordset = func.im_self
        env = recordset.env
        self.model_name = func.im_class._name
        self.method_name = func.im_func.func_name
        self.recordset = recordset

        self.env = env
        self.job_model = self.env['queue.job']

        self.state = PENDING

        self.retry = 0
        if max_retries is None:
            self.max_retries = DEFAULT_MAX_RETRIES
        else:
            self.max_retries = max_retries

        self._uuid = job_uuid

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

        self.user_id = env.uid
        if 'company_id' in env.context:
            company_id = env.context['company_id']
        else:
            company_model = env['res.company']
            company_model = company_model.sudo(self.user_id)
            company_id = company_model._company_default_get(
                object='queue.job',
                field='company_id'
            ).id
        self.company_id = company_id
        self._eta = None
        self.eta = eta

    def perform(self):
        """ Execute the job.

        The job is executed with the user which has initiated it.
        """
        self.retry += 1
        try:
            self.result = self.func(*tuple(self.args), **self.kwargs)
        except RetryableJobError as err:
            if err.ignore_retry:
                self.retry -= 1
                raise
            elif not self.max_retries:  # infinite retries
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

    def store(self):
        """ Store the Job """
        vals = {'state': self.state,
                'priority': self.priority,
                'retry': self.retry,
                'max_retries': self.max_retries,
                'exc_info': self.exc_info,
                'user_id': self.user_id or self.env.uid,
                'company_id': self.company_id,
                'result': unicode(self.result) if self.result else False,
                'date_enqueued': False,
                'date_started': False,
                'date_done': False,
                'eta': False,
                'model_name': self.model_name,
                'method_name': self.method_name,
                'record_ids': self.recordset.ids,
                # TODO: use custom serializer for recordsets
                'args': self.args,
                'kwargs': self.kwargs,
                }

        dt_to_string = odoo.fields.Datetime.to_string
        if self.date_enqueued:
            vals['date_enqueued'] = dt_to_string(self.date_enqueued)
        if self.date_started:
            vals['date_started'] = dt_to_string(self.date_started)
        if self.date_done:
            vals['date_done'] = dt_to_string(self.date_done)
        if self.eta:
            vals['eta'] = dt_to_string(self.eta)

        db_record = self.db_record()
        if db_record:
            db_record.write(vals)
        else:
            date_created = dt_to_string(self.date_created)
            vals.update({'uuid': self.uuid,
                         'name': self.description,
                         'date_created': date_created,
                         })

            self.job_model.sudo().create(vals)

    def db_record(self):
        return self.db_record_from_uuid(self.env, self.uuid)

    @property
    def func(self):
        recordset = self.recordset.with_context(job_uuid=self.uuid)
        recordset = recordset.sudo(self.user_id)
        return getattr(recordset, self.method_name)

    @property
    def description(self):
        if self._description:
            return self._description
        elif self.func.__doc__:
            return self.func.__doc__.splitlines()[0].strip()
        else:
            return '%s.%s' % (self.model_name, self.func.__name__)

    @property
    def uuid(self):
        """Job ID, this is an UUID """
        if self._uuid is None:
            self._uuid = unicode(uuid.uuid4())
        return self._uuid

    @property
    def eta(self):
        return self._eta

    @eta.setter
    def eta(self, value):
        if not value:
            self._eta = None
        elif isinstance(value, timedelta):
            self._eta = datetime.now() + value
        elif isinstance(value, int):
            self._eta = datetime.now() + timedelta(seconds=value)
        else:
            self._eta = value

    def set_pending(self, result=None, reset_retry=True):
        self.state = PENDING
        self.date_enqueued = None
        self.date_started = None
        if reset_retry:
            self.retry = 0
        if result is not None:
            self.result = result

    def set_enqueued(self):
        self.state = ENQUEUED
        self.date_enqueued = datetime.now()
        self.date_started = None

    def set_started(self):
        self.state = STARTED
        self.date_started = datetime.now()

    def set_done(self, result=None):
        self.state = DONE
        self.exc_info = None
        self.date_done = datetime.now()
        if result is not None:
            self.result = result

    def set_failed(self, exc_info=None):
        self.state = FAILED
        if exc_info is not None:
            self.exc_info = exc_info

    def __repr__(self):
        return '<Job %s, priority:%d>' % (self.uuid, self.priority)

    def _get_retry_seconds(self, seconds=None):
        retry_pattern = self.func.retry_pattern
        if not seconds and retry_pattern:
            # ordered from higher to lower count of retries
            patt = sorted(retry_pattern.iteritems(), key=lambda t: t[0])
            seconds = RETRY_INTERVAL
            for retry_count, postpone_seconds in patt:
                if self.retry >= retry_count:
                    seconds = postpone_seconds
                else:
                    break
        elif not seconds:
            seconds = RETRY_INTERVAL
        return seconds

    def postpone(self, result=None, seconds=None):
        """ Write an estimated time arrival to n seconds
        later than now. Used when an retryable exception
        want to retry a job later. """
        eta_seconds = self._get_retry_seconds(seconds)
        self.eta = timedelta(seconds=eta_seconds)
        self.exc_info = None
        if result is not None:
            self.result = result

    def related_action(self, env):
        if not hasattr(self.func, 'related_action'):
            return None
        return self.func.related_action(env, self)


JOB_REGISTRY = set()


def _is_model_method(func):
    return (inspect.ismethod(func) and
            isinstance(func.im_class, odoo.models.MetaModel))


def job(func=None, default_channel='root', retry_pattern=None):
    """ Decorator for jobs.

    Optional argument:

    :param default_channel: the channel wherein the job will be assigned. This
                            channel is set at the installation of the module
                            and can be manually changed later using the views.
    :param retry_pattern: The retry pattern to use for postponing a job.
                          If a job is postponed and there is no eta
                          specified, the eta will be determined from the
                          dict in retry_pattern. When no retry pattern
                          is provided, jobs will be retried after
                          :const:`RETRY_INTERVAL` seconds.
    :type retry_pattern: dict(retry_count,retry_eta_seconds)

    Add a ``delay`` attribute on the decorated function.

    When ``delay`` is called, the function is transformed to a job and
    stored in the Odoo queue.job model. The arguments and keyword
    arguments given in ``delay`` will be the arguments used by the
    decorated function when it is executed.

    ``retry_pattern`` is a dict where keys are the count of retries and the
    values are the delay to postpone a job.

    The ``delay()`` function of a job takes the following arguments:

    env
      Current :py:class:`~odoo.api.Environment`

    model_name
      name of the model on which the job has something to do

    *args and **kargs
     Arguments and keyword arguments which will be given to the called
     function once the job is executed.

     There are 5 special and reserved keyword arguments that you can use:

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

        @api.multi
        @job
        def export_one_thing(self, one_thing):
            # work
            # export one_thing

        env['a.model'].export_one_thing(the_thing_to_export)
        # => normal and synchronous function call

        env['a.model'].with_delay().export_one_thing(the_thing_to_export)
        # => the job will be executed as soon as possible

        delayable = env['a.model'].with_delay(priority=30, eta=60*60*5)
        delayable.export_one_thing(the_thing_to_export)
        # => the job will be executed with a low priority and not before a
        # delay of 5 hours from now

        @job(default_channel='root.subchannel')
        def export_one_thing(one_thing):
            # work
            # export one_thing

        @job(retry_pattern={1: 10 * 60,
                            5: 20 * 60,
                            10: 30 * 60,
                            15: 12 * 60 * 60})
        def retryable_example():
            # 5 first retries postponed 10 minutes later
            # retries 5 to 10 postponed 20 minutes later
            # retries 10 to 15 postponed 30 minutes later
            # all subsequent retries postponed 12 hours later
            raise RetryableJobError('Must be retried later')

        env['a.model'].with_delay().retryable_example()


    See also: :py:func:`related_action` a related action can be attached
    to a job

    """
    if func is None:
        return functools.partial(job, default_channel=default_channel,
                                 retry_pattern=retry_pattern)

    def delay_from_model(*args, **kwargs):
        raise AttributeError(
            "method.delay() can no longer be used, the general form is "
            "env['res.users'].with_delay().method()"
            )

    assert default_channel == 'root' or default_channel.startswith('root.'), (
        "The channel path must start by 'root'")
    assert retry_pattern is None or isinstance(retry_pattern, dict), (
        "retry_pattern must be a dict"
    )

    if not _is_model_method(func):
        raise TypeError('@job can only be used on methods of Models')

    inner_func = func.__func__
    delay_func = delay_from_model

    inner_func.delayable = True
    inner_func.delay = delay_func
    inner_func.retry_pattern = retry_pattern
    inner_func.default_channel = default_channel
    JOB_REGISTRY.add(func)
    return func


# TODO: move on models
def related_action(action=lambda env, job: None, **kwargs):
    """ Attach a *Related Action* to a job.

    A *Related Action* will appear as a button on the Odoo view.
    The button will execute the action, usually it will open the
    form view of the record related to the job.

    The ``action`` must be a callable that responds to arguments::

        env, job, **kwargs

    Example usage:

    .. code-block:: python

        def related_action_partner(env, job):
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
        def export_partner(env, partner_id):
            # ...

    The kwargs are transmitted to the action:

    .. code-block:: python

        def related_action_product(env, job, extra_arg=1):
            assert extra_arg == 2
            model = job.args[0]
            product_id = job.args[1]

        @job
        @related_action(action=related_action_product, extra_arg=2)
        def export_product(env, product_id):
            # ...

    """
    def decorate(func):
        if kwargs:
            action_func = functools.partial(action, **kwargs)
        else:
            action_func = action

        if not _is_model_method(func):
            raise ValueError('@related_action can only be used on methods of '
                             'Models')

        inner_func = func.__func__
        inner_func.related_action = action_func
        return func
    return decorate
