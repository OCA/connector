# -*- encoding: utf-8 -*-
##############################################################################
#
#    Author Guewen Baconnier. Copyright Camptocamp SA
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
import time
import logging
import sys
import traceback
from openerp.osv.orm import Model
from openerp.osv import fields
from tools import DEFAULT_SERVER_DATETIME_FORMAT
import simplejson
from base_external_referentials.external_osv import ExternalSession
from base_external_referentials.decorator import commit_now

MODEL_WITH_UNIQUE_REPORT_LINE = [
    'product.product',
    'product.category',
    ]


class external_report(Model):
    _name = 'external.report'
    _description = 'External Report'
    _order = 'name desc'


    def _get_full_name(self, cr, uid, ids, name, arg, context=None):
        res = {}
        model_obj = self.pool.get('ir.model')
        for report in self.browse(cr, uid, ids, context=context):
            obj = self.pool.get(report.sync_from_object_model.model)
            object_name = obj.browse(cr, uid, report.sync_from_object_id, context=context)
            name = "%s %s from %s"%(report.action, report.action_on.name, object_name.name)
            name = name.replace('_', ' ').lower().strip()
            res[report.id] = name
        return res

    _columns = {
        'name': fields.function(_get_full_name, store=True, type='char', size=256, string='Name'),
        'action': fields.char('Action', size=256, required=True, readonly=True),
        'action_on': fields.many2one('ir.model', 'Action On',required=True, readonly=True),
        'sync_from_object_model': fields.many2one('ir.model', 'Sync From Object',
                                                        required=True, readonly=True),
        'sync_from_object_id': fields.integer('Sync From Object ID', required=True, readonly=True),
        'referential_id': fields.many2one('external.referential','External Referential',
                                                        required=True,readonly=True),
        'line_ids': fields.one2many('external.report.line','report_id', 'Report Lines'),
        'failed_line_ids': fields.one2many('external.report.line', 'report_id',
                                        'Failed Report Lines', domain=[('state', '!=', 'success')]),
        'history_ids': fields.one2many('external.report.history','report_id', 'History'),
        'email_tmpl_id': fields.many2one('email.template', 'Email Template', help="Email template used to send an email every time a failed report line is created"),
    }

    def _get_report(self, cr, uid, action, action_on, sync_from_object, context=None):
        report_id = self.search(cr, uid,
                [
                    ('action', '=', action),
                    ('action_on', '=', action_on),
                    ('sync_from_object_model', '=', sync_from_object._name),
                    ('sync_from_object_id', '=', sync_from_object.id),
                ], context=context)
        return report_id and report_id[0] or False

    def _clean_successful_lines(self, cr, uid, report_id, context=None):
        lines_obj = self.pool.get('external.report.line')
        line_ids = lines_obj.search(cr, uid,
                                    [('report_id', '=', report_id),
                                    ('state', '=', 'success')],
                                    context=context)
        lines_obj.unlink(cr, uid, line_ids, context=context)
        return True

    def retry_failed_lines(self, cr, uid, ids, context=None):
        logging.getLogger('external_synchro').info("retry the failed lines of the reports ids %s" % (ids,))
        if isinstance(ids, int):
            ids = [ids]
        if context is None:
            context={}
        context['origin'] = 'retry'
        for report in self.read(cr, uid, ids, ['failed_line_ids'], context=context):
            failed_line_ids = report['failed_line_ids']
            if failed_line_ids:
                context['report_id'] = report['id']
                self.pool.get('external.report.line').retry(cr, uid, failed_line_ids, context=context)
        return True

    def _prepare_start_report(self, cr, uid, action, action_on, sync_from_object, context=None):
        model_obj = self.pool.get('ir.model')
        model_id = model_obj.search(cr, uid, [['model', '=', sync_from_object._name]])[0]
        action_on_model_id = model_obj.search(cr, uid, [['model', '=', action_on]])[0]
        return {
            'action': action,
            'action_on': action_on_model_id,
            'sync_from_object_model': model_id,
            'sync_from_object_id': sync_from_object.id,
            'referential_id': sync_from_object.id if sync_from_object._name == 'external.referential' else sync_from_object.referential_id.id,
        }

    @commit_now
    def start_report(self, cr, uid, external_session, id=None, action=None,
                            action_on=None, context=None):
        """ Start a report, use the report with the id in the parameter
        if given. Otherwise, try to find the report which have the same method
         and object (we use the same report to avoid a
         multiplication of reports) If nothing is found, it create a new report
        """

        if not id and not (action and action_on):
            raise Exception('No reference to create the report!')
        if id:
            report_id = id
        else:
            report_id = self._get_report(cr, uid, action, action_on, external_session.sync_from_object, context)

        if report_id:
            self._clean_successful_lines(cr, uid, report_id, context)
        else:
            report_id = self.create(
                cr, uid,
                self._prepare_start_report(
                    cr, uid, action, action_on, external_session.sync_from_object, context=context),
                context=context)
        history_id = self.pool.get('external.report.history').create(
            cr, uid,
            {'report_id': report_id,
             'user_id': uid,
             'start_date': time.strftime(DEFAULT_SERVER_DATETIME_FORMAT)},
            context=context)
        external_session.tmp['history_id'] = history_id
        return report_id

    @commit_now
    def end_report(self, cr, uid, external_session, id, context=None):
        """ Create history lines based on lines
        Successful lines are cleaned at each start of a report
        so we historize their aggregation.
        """
        history_obj = self.pool.get('external.report.history')
        history_obj.write(cr, uid, external_session.tmp['history_id'],
            {'end_date': time.strftime(DEFAULT_SERVER_DATETIME_FORMAT)},
            context=context)
        return id

    def delete_failed_lines(self, cr, uid, ids, context=None):
        if isinstance(ids, int):
            ids = [ids]
        for report in self.read(cr, uid, ids, ['failed_line_ids'], context=context):
            failed_line_ids = report['failed_line_ids']
            if failed_line_ids:
                self.pool.get('external.report.line').unlink(cr, uid, failed_line_ids, context=context)
        return True


class external_report_history(Model):
    _name = 'external.report.history'
    _description = 'External Report History'
    _rec_name = 'report_id'
    _order = 'start_date desc'

    _columns = {
        'report_id': fields.many2one('external.report',
                                              'External Report',
                                              required=True,
                                              readonly=True,
                                              ondelete='cascade'),
        'start_date': fields.datetime('Start Date', required=True, readonly=True),
        'end_date': fields.datetime('End Date', readonly=True),
        'count_success': fields.integer('Count Success', readonly=True),
        'count_failed': fields.integer('Count Failed', readonly=True),
        'user_id': fields.many2one('res.users', 'User', required=True, readonly=True),
    }

    _defaults = {
        "start_date": lambda *a: time.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
     }

    def add_one_fail(self, cr, uid, history_id, context=None):
        return self._add_one(cr, uid, history_id, 'fail', context=context)

    def add_one_success(self, cr, uid, history_id, context=None):
        return self._add_one(cr, uid, history_id, 'success', context=context)

    @commit_now
    def _add_one(self, cr, uid, history_id, state, context=None):
        history = self.browse(cr, uid, history_id, context=context)
        if state == 'fail':
            vals = {'count_failed': history.count_failed + 1}
        else:
            vals = {'count_success': history.count_success + 1}
        self.write(cr, uid, history_id, vals, context=context)
        return True


class external_report_lines(Model):
    _name = 'external.report.line'
    _description = 'External Report Lines'
    _rec_name = 'res_id'
    _order = 'date desc'

    def _get_resource(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for report_line in self.browse(cr, uid, ids, context=context):
            res[report_line.id] = {
                'resource_text': simplejson.dumps(report_line.resource),
                'args_text': simplejson.dumps(report_line.args),
                'kwargs_text': simplejson.dumps(report_line.kwargs),
            }
        return res

    def _set_resource(self, cr, uid, ids, field_name, field_value, arg, context=None):
        res = {}
        if isinstance(ids, int) or isinstance(ids, long):
            ids = [ids]
        for report_line in self.browse(cr, uid, ids, context=context):
            self.write(cr, uid, report_line.id, {field_name.replace('_text', ''): simplejson.loads(field_value)})
        return True

    _columns = {
        'report_id': fields.many2one('external.report',
                                              'External Report',
                                              readonly=True,
                                              ondelete='restrict'),
        'state': fields.selection((('success', 'Success'),
                                   ('fail', 'Failed')),
                                   'Status', required=True, readonly=True),
        'action': fields.char('Action', size=256, required=True, readonly=True),
        'action_on': fields.many2one('ir.model', 'Action On',required=True, readonly=True),
        'res_id': fields.integer('Resource Id', readonly=True),
        'date': fields.datetime('Date', required=True, readonly=True),
        'external_id': fields.char('External ID', size=64, readonly=True),
        'error_message': fields.text('Error Message', readonly=True),
        'traceback': fields.text('Traceback', readonly=True),
        'exception_type': fields.char('Exception Type', size=128, readonly=True),
        'resource': fields.serialized('External Data', readonly=True),
        'resource_text':fields.function(_get_resource, fnct_inv=_set_resource, type="text", string='External Data', multi='into_text'),
        'args': fields.serialized('Args', readonly=True),
        'args_text':fields.function(_get_resource, fnct_inv=_set_resource, type="text", string='Args Data', multi='into_text'),
        'kwargs': fields.serialized('Kwargs', readonly=True),
        'kwargs_text':fields.function(_get_resource, fnct_inv=_set_resource, type="text", string='Kwargs Data', multi='into_text'),
    }

    _defaults = {
        "date": lambda *a: time.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
    }

    def get_existing_line_id(self, cr, uid, action_on, action, res_id=None, external_id=None, context=None):
        if context.get('retry_report_line_id'):
            return context['retry_report_line_id']
        elif action_on in MODEL_WITH_UNIQUE_REPORT_LINE:
            existing_line_id = self.search(cr, uid, [
                              ('action_on', '=', action_on),
                              ('action', '=', action),
                              ('res_id', '=', res_id),
                              ('external_id', '=', external_id),
                        ], context=context)
            return existing_line_id and existing_line_id[0] or False
        return False

    #TODO
    #1 - Did it usefull to log sucessfull entry?
    #2 - We should not recreate a new entry for an existing line created from a previous report
    #3 - Move the existing line id in the external_session.tmp ;)
    @commit_now
    def start_log(self, cr, uid, action_on, action, res_id=None,
                  external_id=None, resource=None, args=None, kwargs=None):
        context = kwargs.get('context') or {}
        existing_line_id = self.get_existing_line_id(cr, uid,action_on, action,
                                          res_id=res_id, external_id=external_id, context=context)
        report_id = context.get('report_id')

        if existing_line_id:
            self.write(cr, uid,
                           existing_line_id,
                           {'state': 'fail',
                            'date': time.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                            'res_id': res_id,
                            'external_id': external_id,
                            'args': args,
                            'kwargs': kwargs,
                            })
        else:
            action_on_model_id = self.pool.get('ir.model').search(cr, uid, [['model', '=', action_on]])[0]
            existing_line_id = self.create(cr, uid, {
                            'report_id': report_id,
                            'state': 'fail',
                            'action_on': action_on_model_id,
                            'action': action,
                            'date': time.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                            'res_id': res_id,
                            'external_id': external_id,
                            'resource': resource,
                            'args': args,
                            'kwargs': kwargs,
                        })
        return existing_line_id

    def log_fail(self, cr, uid, external_session, report_line_id, error_message, context=None):
        self._log_fail(cr, uid, external_session, report_line_id, error_message, context=context)
        if not context.get('no_mail'):
            self._send_mail(cr, uid, report_line_id, context=context)
        return True

    @commit_now
    def _log_fail(self, cr, uid, external_session, report_line_id, error_message, context=None):
        exc_type, exc_value, exc_traceback = sys.exc_info()
        if external_session:
            external_session.logger.exception(error_message)
        self.write(cr, uid, report_line_id, {
                            'error_message': error_message,
                            'exception_type': exc_type,
                            'traceback': ''.join(traceback.format_exception(
                                exc_type, exc_value, exc_traceback)),
                            'state': 'fail',
                            }, context=context)
        if external_session and external_session.tmp.get('history_id'):
            self.pool.get('external.report.history').add_one_fail(cr, uid, \
                                            external_session.tmp['history_id'], context=context)
        return True

    @commit_now
    def _send_mail(self, cr, uid, report_line_id, context=None):
        line = self.browse(cr, uid, report_line_id, context=context)
        if line.report_id.email_tmpl_id:
            self.pool.get('email.template').send_mail(cr, uid, line.report_id.email_tmpl_id.id,\
                                                  report_line_id, force_send=True, context=context)
        return True
    
    @commit_now
    def log_success(self, cr, uid, external_session, report_line_id, context=None):
        self.write(cr, uid, report_line_id, {'state': 'success'}, context=context)
        if external_session and external_session.tmp.get('history_id'):
            self.pool.get('external.report.history').add_one_success(cr, uid, \
                                            external_session.tmp['history_id'], context=context)
        return True

    def retry(self, cr, uid, ids, context=None):
        if isinstance(ids, int) or isinstance(ids, long):
            ids = [ids]

        for log in self.browse(cr, uid, ids, context=context):
            method = getattr(self.pool.get(log.action_on.model), log.action)
            args = log.args
            kwargs = log.kwargs
            if log.report_id:
                sync_from_object = self.pool.get(log.report_id.sync_from_object_model.model).\
                                    browse(cr, uid, log.report_id.sync_from_object_id, context=context)
                external_session = ExternalSession(log.report_id.referential_id, sync_from_object)
                resource = log.resource
                if not kwargs.get('context', False):
                    kwargs['context']={}

                #don't send email when retry
                kwargs['context']['no_mail'] = True
                # keep the id of the line to update it with the result
                kwargs['context']['retry_report_line_id'] = log.id

                method(cr, uid, external_session, resource, *args, **kwargs)
            else:
                if not kwargs.get('context', False):
                    kwargs['context']={}
                #don't send email when retry
                kwargs['context']['no_mail'] = True
                kwargs['context']['retry_report_line_id'] = log.id
                method(cr, uid, *args, **kwargs)
        return True

    def aggregate_actions(self, cr, uid, ids, context=None):
        res = {}
        for line in self.browse(cr, uid, ids, context=context):
            state = line.state
            model = line.res_model
            action = line.action

            if not res.get((state, model, action), False):
                res[(state, model, action)] = 0
            res[(state, model, action)] += 1

        return res

