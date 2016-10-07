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
from datetime import datetime, timedelta

from odoo import models, fields, api, exceptions, _

from ..job import STATES, DONE, PENDING, Job, JOB_REGISTRY
from ..utils import get_odoo_module, is_module_installed
from ..exception import RetryableJobError
from ..fields import JobSerialized

_logger = logging.getLogger(__name__)


def channel_func_name(method):
    return '<%s>.%s' % (method.im_class._name, method.__name__)


class QueueJob(models.Model):
    """ Job status and result """
    _name = 'queue.job'
    _description = 'Queue Job'
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    _log_access = False

    _order = 'date_created DESC, date_done DESC'

    _removal_interval = 30  # days

    uuid = fields.Char(string='UUID',
                       readonly=True,
                       index=True,
                       required=True)
    user_id = fields.Many2one(comodel_name='res.users',
                              string='User ID',
                              required=True)
    company_id = fields.Many2one(comodel_name='res.company',
                                 string='Company', index=True)
    name = fields.Char(string='Description', readonly=True)

    model_name = fields.Char(string='Model', readonly=True)
    method_name = fields.Char(readonly=True)
    record_ids = fields.Serialized(readonly=True)
    args = JobSerialized(readonly=True)
    kwargs = JobSerialized(readonly=True)
    func_string = fields.Char(string='Task', compute='_compute_func_string',
                              readonly=True, store=True)

    state = fields.Selection(STATES,
                             string='State',
                             readonly=True,
                             required=True,
                             index=True)
    priority = fields.Integer()
    exc_info = fields.Text(string='Exception Info', readonly=True)
    result = fields.Text(string='Result', readonly=True)

    date_created = fields.Datetime(string='Created Date', readonly=True)
    date_started = fields.Datetime(string='Start Date', readonly=True)
    date_enqueued = fields.Datetime(string='Enqueue Time', readonly=True)
    date_done = fields.Datetime(string='Date Done', readonly=True)

    eta = fields.Datetime(string='Execute only after')
    retry = fields.Integer(string='Current try')
    max_retries = fields.Integer(
        string='Max. retries',
        help="The job will fail if the number of tries reach the "
             "max. retries.\n"
             "Retries are infinite when empty.",
    )
    channel_method_name = fields.Char(readonly=True,
                                      compute='_compute_channel',
                                      store=True)
    job_function_id = fields.Many2one(comodel_name='queue.job.function',
                                      compute='_compute_channel',
                                      string='Job Function',
                                      readonly=True,
                                      store=True)
    # for searching without JOIN on channels
    channel = fields.Char(compute='_compute_channel', store=True, index=True)

    @api.multi
    @api.depends('model_name', 'method_name', 'job_function_id.channel_id')
    def _compute_channel(self):
        for record in self:
            model = self.env[record.model_name]
            method = getattr(model, record.method_name)
            channel_method_name = channel_func_name(method)
            func_model = self.env['queue.job.function']
            function = func_model.search([('name', '=', channel_method_name)])
            record.channel_method_name = channel_method_name
            record.job_function_id = function
            record.channel = record.job_function_id.channel

    @api.multi
    @api.depends('model_name', 'method_name', 'record_ids', 'args', 'kwargs')
    def _compute_func_string(self):
        for record in self:
            record_ids = record.record_ids
            model = repr(self.env[record.model_name].browse(record_ids))
            args = [repr(arg) for arg in record.args]
            kwargs = ['%s=%r' % (key, val) for key, val
                      in record.kwargs.iteritems()]
            all_args = ', '.join(args + kwargs)
            record.func_string = (
                "%s.%s(%s)" % (model, record.method_name, all_args)
            )

    @api.multi
    def open_related_action(self):
        """ Open the related action associated to the job """
        self.ensure_one()
        job = Job.load(self.env, self.uuid)
        action = job.related_action(self.env)
        if action is None:
            raise exceptions.Warning(_('No action available for this job'))
        return action

    @api.multi
    def _change_job_state(self, state, result=None):
        """ Change the state of the `Job` object itself so it
        will change the other fields (date, result, ...)
        """
        for job in self:
            job = Job.load(job.env, job.uuid)
            if state == DONE:
                job.set_done(result=result)
            elif state == PENDING:
                job.set_pending(result=result)
            else:
                raise ValueError('State not supported: %s' % state)
            job.store()

    @api.multi
    def button_done(self):
        result = _('Manually set to done by %s') % self.env.user.name
        self._change_job_state(DONE, result=result)
        return True

    @api.multi
    def requeue(self):
        self._change_job_state(PENDING)
        return True

    @api.multi
    def write(self, vals):
        res = super(QueueJob, self).write(vals)
        if vals.get('state') == 'failed':
            # subscribe the users now to avoid to subscribe them
            # at every job creation
            self._subscribe_users()
            for job in self:
                msg = job._message_failed_job()
                if msg:
                    job.message_post(body=msg,
                                     subtype='queue_job.mt_job_failed')
        return res

    @api.multi
    def _subscribe_users(self):
        """ Subscribe all users having the 'Queue Job Manager' group """
        group = self.env.ref('queue_job.group_queue_job_manager')
        if not group:
            return
        companies = self.mapped('company_id')
        domain = [('groups_id', '=', group.id)]
        if companies:
            domain.append(('company_id', 'child_of', companies.ids))
        users = self.env['res.users'].search(domain)
        self.message_subscribe_users(user_ids=users.ids)

    @api.multi
    def _message_failed_job(self):
        """ Return a message which will be posted on the job when it is failed.

        It can be inherited to allow more precise messages based on the
        exception informations.

        If nothing is returned, no message will be posted.
        """
        self.ensure_one()
        return _("Something bad happened during the execution of the job. "
                 "More details in the 'Exception Information' section.")

    @api.model
    def _needaction_domain_get(self):
        """ Returns the domain to filter records that require an action
            :return: domain or False is no action
        """
        return [('state', '=', 'failed')]

    @api.model
    def autovacuum(self):
        """ Delete all jobs done since more than ``_removal_interval`` days.

        Called from a cron.
        """
        deadline = datetime.now() - timedelta(days=self._removal_interval)
        jobs = self.search(
            [('date_done', '<=', fields.Datetime.to_string(deadline))],
        )
        jobs.unlink()
        return True

    @api.multi
    def testing_method(self, *args, **kwargs):
        """ Method used for tests

        Return always the arguments and keyword arguments received
        """
        if kwargs.get('raise_retry'):
            raise RetryableJobError('Must be retried later')
        if kwargs.get('return_context'):
            return self.env.context
        return (args, kwargs)


class RequeueJob(models.TransientModel):
    _name = 'queue.requeue.job'
    _description = 'Wizard to requeue a selection of jobs'

    @api.model
    def _default_job_ids(self):
        res = False
        context = self.env.context
        if (context.get('active_model') == 'queue.job' and
                context.get('active_ids')):
            res = context['active_ids']
        return res

    job_ids = fields.Many2many(comodel_name='queue.job',
                               string='Jobs',
                               default=_default_job_ids)

    @api.multi
    def requeue(self):
        jobs = self.job_ids
        jobs.requeue()
        return {'type': 'ir.actions.act_window_close'}


class JobChannel(models.Model):
    _name = 'queue.job.channel'
    _description = 'Job Channels'

    name = fields.Char()
    complete_name = fields.Char(compute='_compute_complete_name',
                                string='Complete Name',
                                store=True,
                                readonly=True)
    parent_id = fields.Many2one(comodel_name='queue.job.channel',
                                string='Parent Channel',
                                ondelete='restrict')
    job_function_ids = fields.One2many(comodel_name='queue.job.function',
                                       inverse_name='channel_id',
                                       string='Job Functions')

    _sql_constraints = [
        ('name_uniq',
         'unique(complete_name)',
         'Channel complete name must be unique'),
    ]

    @api.multi
    @api.depends('name', 'parent_id', 'parent_id.name')
    def _compute_complete_name(self):
        for record in self:
            if not record.name:
                return  # new record
            channel = record
            parts = [channel.name]
            while channel.parent_id:
                channel = channel.parent_id
                parts.append(channel.name)
            record.complete_name = '.'.join(reversed(parts))

    @api.multi
    @api.constrains('parent_id', 'name')
    def parent_required(self):
        for record in self:
            if record.name != 'root' and not record.parent_id:
                raise exceptions.ValidationError(_('Parent channel required.'))

    @api.multi
    def write(self, values):
        for channel in self:
            if (not self.env.context.get('install_mode') and
                    channel.name == 'root' and
                    ('name' in values or 'parent_id' in values)):
                raise exceptions.Warning(_('Cannot change the root channel'))
        return super(JobChannel, self).write(values)

    @api.multi
    def unlink(self):
        for channel in self:
            if channel.name == 'root':
                raise exceptions.Warning(_('Cannot remove the root channel'))
        return super(JobChannel, self).unlink()

    @api.multi
    def name_get(self):
        result = []
        for record in self:
            result.append((record.id, record.complete_name))
        return result


class JobFunction(models.Model):
    _name = 'queue.job.function'
    _description = 'Job Functions'
    _log_access = False

    @api.model
    def _default_channel(self):
        return self.env.ref('queue_job.channel_root')

    name = fields.Char(index=True)
    channel_id = fields.Many2one(comodel_name='queue.job.channel',
                                 string='Channel',
                                 required=True,
                                 default=_default_channel)
    channel = fields.Char(related='channel_id.complete_name',
                          store=True,
                          readonly=True)

    @api.model
    def _find_or_create_channel(self, channel_path):
        channel_model = self.env['queue.job.channel']
        parts = channel_path.split('.')
        parts.reverse()
        channel_name = parts.pop()
        assert channel_name == 'root', "A channel path starts with 'root'"
        # get the root channel
        channel = channel_model.search([('name', '=', channel_name)])
        while parts:
            channel_name = parts.pop()
            parent_channel = channel
            channel = channel_model.search([
                ('name', '=', channel_name),
                ('parent_id', '=', parent_channel.id)],
                limit=1,
            )
            if not channel:
                channel = channel_model.create({
                    'name': channel_name,
                    'parent_id': parent_channel.id,
                })
        return channel

    @api.model
    def _register_jobs(self):
        for func in JOB_REGISTRY:
            if not is_module_installed(self.env, get_odoo_module(func)):
                continue
            func_name = channel_func_name(func)
            if not self.search_count([('name', '=', func_name)]):
                channel = self._find_or_create_channel(func.default_channel)
                self.create({'name': func_name, 'channel_id': channel.id})

    @api.model
    def _setup_complete(self):
        super(JobFunction, self)._setup_complete()
        self._register_jobs()
