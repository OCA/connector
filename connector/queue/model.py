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

import openerp
from openerp import tools
from openerp.osv import orm, fields
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp.tools.translate import _
from openerp import exceptions
from openerp import SUPERUSER_ID

from .job import STATES, DONE, PENDING, OpenERPJobStorage, JOB_REGISTRY
from .worker import WORKER_TIMEOUT
from ..session import ConnectorSession
from .worker import watcher
from ..connector import get_openerp_module, is_module_installed

_logger = logging.getLogger(__name__)

DEFAULT_LIMIT = 1000

class QueueJob(orm.Model):
    """ Job status and result """
    _name = 'queue.job'
    _description = 'Queue Job'
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    _log_access = False

    _order = 'date_created DESC, date_done DESC'

    _removal_interval = 30  # days

    def _job_function_mapping_function(self, cr, uid, trigger_ids,
                                       context=None):
        res = self.pool['queue.job.function'].read(
            cr, uid, trigger_ids, ['name'], context=context)
        names = [r['name'] for r in res]
        return self.pool['queue.job'].search(
            cr, uid, [('func_name', 'in', names)], context=context)

    def _compute_channel(self, cr, uid, ids, field_names=None,
                         arg=False, context=None):
        res = dict.fromkeys(ids)
        func_model = self.pool['queue.job.function']
        channel_model = self.pool['queue.job.channel']
        for info in self.read(cr, uid, ids, ['func_name', 'company_id'],
                              context=context):
            val = {'job_function_id': False,
                   'channel': False}
            func_id = func_model.search(
                cr, uid, [('name', '=', info['func_name'])], context=context)
            if func_id:
                function = func_model.browse(cr, uid, func_id[0],
                                             context=context)
                val['job_function_id'] = function.id
                channel = function.channel_id.complete_name
                if function.channel_id.channel_by_company \
                        and info['company_id']:
                    channel_company = '%s_%s' % (channel,
                                                 info['company_id'][0])
                    channel_id = channel_model.search(cr, uid, [
                        ('complete_name', '=', channel_company)])
                    if channel_id:
                        channel = channel_company
                val['channel'] = channel
            res[info['id']] = val
        return res

    _columns = {
        'worker_id': fields.many2one('queue.worker', string='Worker',
                                     ondelete='set null', readonly=True,
                                     select=True),
        'uuid': fields.char('UUID', readonly=True, select=True, required=True),
        'user_id': fields.many2one('res.users', string='User ID',
                                   required=True),
        'company_id': fields.many2one('res.company', 'Company', select=True),
        'name': fields.char('Description', readonly=True),
        'func_string': fields.char('Task', readonly=True),
        'func': fields.binary('Pickled Function', readonly=True,
                              required=True),
        'state': fields.selection(STATES,
                                  string='State',
                                  readonly=True,
                                  required=True,
                                  select=True),
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
            help="The job will fail if the number of tries reach the "
                 "max. retries.\n"
                 "Retries are infinite when empty."),
        'func_name': fields.char(readonly=True, string='func_name'),
        'job_function_id': fields.function(
            _compute_channel, type='many2one', obj='queue.job.function',
            string='Job Function',
            store={'queue.job.function':
                   (_job_function_mapping_function,
                    ['channel_id'], 10),
                   'queue.job':
                   ((lambda self, cr, uid, ids, c={}: ids),
                    ['func_name'], 10)},
            readonly=True, multi=True),
        # for searching without JOIN on channels
        'channel': fields.function(
            _compute_channel, string='Channel', type='char',
            store={'queue.job.function':
                   (_job_function_mapping_function,
                    ['channel_id'], 10),
                   'queue.job':
                   ((lambda self, cr, uid, ids, c={}: ids),
                    ['func_name'], 10)},
            select=True, multi=True)

    }

    _defaults = {
        'active': True,
    }

    def open_related_action(self, cr, uid, ids, context=None):
        """ Open the related action associated to the job """
        if hasattr(ids, '__iter__'):
            assert len(ids) == 1, "1 ID expected, got %s" % ids
            ids = ids[0]
        session = ConnectorSession(cr, uid, context=context)
        storage = OpenERPJobStorage(session)
        job = self.browse(cr, uid, ids, context=context)
        job = storage.load(job.uuid)
        action = job.related_action(session)
        if action is None:
            raise orm.except_orm(
                _('Error'),
                _('No action available for this job'))
        return action

    def _change_job_state(self, cr, uid, ids, state, result=None,
                          context=None):
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
            for job_id in ids:
                msg = self._message_failed_job(cr, uid, job_id,
                                               context=context)
                if msg:
                    self.message_post(cr, uid, job_id, body=msg,
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
        jobs = self.read(cr, uid, ids, ['company_id'], context=context)
        company_ids = [val['company_id'][0] for val in jobs
                       if val['company_id']]
        domain = [('groups_id', '=', group_id)]
        if company_ids:
            domain.append(('company_ids', 'child_of', company_ids))
        user_ids = self.pool.get('res.users').search(
            cr, uid, domain, context=context)
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

    def autovacuum(self, cr, uid, limit=None, context=None):
        """ Delete all jobs (active or not) done since more than
        ``_removal_interval`` days limited by ``limit``.

        Called from a cron.

        :param limit: optional maximum number of records to delete at once
        :type limit: int
        """
        if context is None:
            context = {}
        context = dict(context, active_test=False)
        deadline = datetime.now() - timedelta(days=self._removal_interval)
        deadline_fmt = deadline.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        while True:
            job_ids = self.search(cr, uid,
                                [('date_done', '<=', deadline_fmt)],
                                limit=limit or DEFAULT_LIMIT,
                                context=context)
            if not job_ids:
                break
            self.unlink(cr, uid, job_ids, context=context)
            cr.commit()
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
            # Here it's likely that the FOR UPDATE NOWAIT failed to get
            # the LOCK, so we ROLLBACK to the SAVEPOINT to restore the
            # transaction to its earlier state. The assign will be done
            # the next time.
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

        try:
            worker_id = self._worker_id(cr, uid, context=context)
        except AssertionError as e:
            _logger.exception(e)
            return
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
        try:
            db_worker_id = self._worker_id(cr, uid, context=context)
        except AssertionError as e:
            _logger.exception(e)
            return
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


class JobChannel(orm.Model):
    _name = 'queue.job.channel'
    _description = 'Job Channels'

    def _get_subchannels(self, cr, uid, ids, context=None):
        """ return all sub channel of the given channel (included) """
        res = []
        for m in self.browse(cr, uid, ids, context=context):
            res.append(m.id)
            while m.parent_id:
                res.append(m.parent_id.id)
                m = m.parent_id
        return res

    def _compute_complete_name(self, cr, uid, ids, name, args, context=None):
        res = {}
        for m in self.browse(cr, uid, ids, context=context):
            channel = m
            parts = [m.name]
            while channel.parent_id:
                channel = channel.parent_id
                parts.append(channel.name)
            res[m.id] = '.'.join(reversed(parts))
        return res

    _columns = {
        'name':  fields.char(string='Name'),
        'complete_name':  fields.function(
            _compute_complete_name, type='char', string='Complete Name',
            store={'queue.job.channel':
                   (_get_subchannels,
                    ['name', 'parent_id', 'parent_id.name'], 10)},
            readonly=True),
        'parent_id': fields.many2one('queue.job.channel',
                                     string='Parent Channel',
                                     ondelete='restrict'),
        'job_function_ids': fields.one2many('queue.job.function',
                                             fields_id='channel_id',
                                             string='Job Functions'),
        'channel_by_company': fields.boolean(
            'Channel by Company',
            help=("determine if this channel should be defined by company,"
                  "a company channel is identified by "
                  "<channel_name>_<company_id>"))
    }

    _sql_constraints = [
        ('name_uniq',
         'unique(complete_name)',
         _('Channel complete name must be unique')),
    ]

    def parent_required(self, cr, uid, ids, context=None):
        for channel in self.browse(cr, uid, ids, context=context):
            if channel.name != 'root' and not channel.parent_id:
                return False
        return True

    _constraints = [
        (parent_required,
         _('Parent channel required.'),
         ['parent_id', 'name'])
    ]

    def create(self, cr, uid, values, context=None):
        res = super(JobChannel, self).create(cr, uid, values, context=context)
        if values.get('channel_by_company'):
            # create company channel
            company_ids = self.pool['res.company'].search(
                cr, SUPERUSER_ID, [], context=context)

            for company_id in company_ids:
                channel_name = '%s_%s' % (values['name'], company_id)
                self.copy(cr, uid, res,
                          {'name': channel_name,
                           'job_function_ids': False,
                           'channel_by_company': False}, context=context)

        return res

    def write(self, cr, uid, ids, values, context=None):
        if not hasattr(ids, '__iter__'):
            ids = [ids]
        context = context or {}

        channel_by_name = {}

        for channel in self.browse(cr, uid, ids, context=context):
            if (not context.get('install_mode') and
                    channel.name == 'root' and
                    ('name' in values or 'parent_id' in values)):
                raise exceptions.Warning(_('Cannot change the root channel'))
            channel_by_name[channel.id] = \
                {'name': channel.name, 'complete_name': channel.complete_name}

        if 'channel_by_company' in values.keys():
            company_ids = self.pool['res.company'].search(
                cr, SUPERUSER_ID, [], context=context)

            for company_id in company_ids:
                for channel_id in ids:
                    channel = channel_by_name[channel_id]
                    channel_name = '%s_%s' % (channel['name'],
                                              company_id)
                    channel_complete_name = '%s_%s' % (
                        channel['complete_name'], company_id)
                    if values['channel_by_company']:
                        # create channel by company
                        self.copy(cr, uid, channel_id,
                                  {'name': channel_name,
                                   'job_function_ids': False,
                                   'channel_by_company': False},
                                  context=context)
                    else:
                        # remove channel by company
                        channel_ids = self.search(
                            cr, uid, [('complete_name', '=',
                                       channel_complete_name)],
                            context=context)
                        if channel_ids:
                            self.unlink(cr, uid, channel_ids, context=context)

        return super(JobChannel, self).write(cr, uid, ids, values,
                                             context=context)

    def unlink(self, cr, uid, ids, context=None):
        if not hasattr(ids, '__iter__'):
            ids = [ids]
        company_ids = self.pool['res.company'].search(
            cr, SUPERUSER_ID, [], context=context)
        for channel in self.browse(cr, uid, ids, context=context):
            if channel.name == 'root':
                raise exceptions.Warning(_('Cannot remove the root channel'))
            if channel.channel_by_company:
                # remove company channel
                for company_id in company_ids:
                    channel_complete_name = '%s_%s' % (
                        channel.complete_name, company_id)
                    channel_ids = self.search(
                        cr, uid, [('complete_name', '=',
                                   channel_complete_name)],
                        context=context)
                    if channel_ids:
                        self.unlink(cr, uid, channel_ids, context=context)
        return super(JobChannel, self).unlink(cr, uid, ids, context=context)

    def name_get(self, cr, uid, ids, context=None):
        if not ids:
            return []
        res = []
        for channel in self.browse(cr, uid, ids, context=context):
            res.append((channel.id, channel.complete_name))
        return res


class JobFunction(orm.Model):
    _name = 'queue.job.function'
    _description = 'Job Functions'
    _log_access = False

    def _default_channel(self, cr, uid, context=None):
        return self.pool.get('ir.model.data').get_object_reference(
            cr, uid, 'connector', 'channel_root')[1]

    _columns = {
        'name': fields.char(select=True, string='Name'),
        'channel_id': fields.many2one('queue.job.channel',
                                      string='Channel',
                                      required=True),
        'channel': fields.related('channel_id', 'complete_name', type='char',
                                  store=True,
                                  readonly=True),
    }

    _defaults = {
        'channel_id': _default_channel,
    }

    def _find_or_create_channel(self, cr, uid, channel_path, context=None):
        channel_model = self.pool['queue.job.channel']
        parts = channel_path.split('.')
        parts.reverse()
        channel_name = parts.pop()
        assert channel_name == 'root', "A channel path starts with 'root'"
        # get the root channel
        channel_id = channel_model.search(
            cr, uid, [('name', '=', channel_name)])[0]
        while parts:
            channel_name = parts.pop()
            parent_channel_id = channel_id
            channel_ids = channel_model.search(cr, uid, [
                ('name', '=', channel_name),
                ('parent_id', '=', channel_id)],
                limit=1,
            )
            if channel_ids:
                channel_id = channel_ids[0]
            else:
                channel_id = channel_model.create(cr, uid, {
                    'name': channel_name,
                    'parent_id': parent_channel_id,
                })
        return channel_id

    def _register_jobs(self, cr):
        for func in JOB_REGISTRY:
            if not is_module_installed(self.pool, get_openerp_module(func)):
                continue
            func_name = '%s.%s' % (func.__module__, func.__name__)
            if not self.search_count(
                    cr, openerp.SUPERUSER_ID, [('name', '=', func_name)]):
                channel_id = self._find_or_create_channel(
                    cr, openerp.SUPERUSER_ID, func.default_channel)
                self.create(cr, openerp.SUPERUSER_ID,
                            {'name': func_name,
                             'channel_id': channel_id})

    def _register_hook(self, cr):
        vals = super(JobFunction, self)._register_hook(cr)
        self._register_jobs(cr)
        if not tools.config.options['test_enable']:
            cr.commit()
        return vals
