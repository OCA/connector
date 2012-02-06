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
import pooler
from osv import osv, fields
from tools.translate import _
from tools.safe_eval import safe_eval


class external_report(osv.osv):
    _name = 'external.report'
    _description = 'External Report'
    _order = 'end_date desc'

    _columns = {
        'name': fields.char('Report Name', size=32, required=True,
                            readonly=True),
        'ref': fields.char('Report Reference', size=64, required=True,
                           readonly=True,
                           help="Internal reference which represents "
                                "the action like export catalog "
                                "or import orders"),
        'start_date': fields.datetime('Last Start Date', readonly=True),
        'end_date': fields.datetime('Last End Date', readonly=True),
        'external_referential_id': fields.many2one('external.referential',
                                                   'External Referential',
                                                   required=True,
                                                   readonly=True),
        'line_ids': fields.one2many('external.report.line',
                                    'external_report_id', 'Report Lines'),
        'failed_line_ids': fields.one2many('external.report.line',
                                           'external_report_id',
                                           'Failed Report Lines',
                                           domain=[('state', '=', 'fail')]),
        'history_ids': fields.one2many('external.report.history',
                                       'external_report_id', 'History'),
    }

    def get_report_by_ref(self, cr, uid, ref, external_referential_id,
                          context=None):
        report_id = False
        report = self.search(cr, uid,
                           [('ref', '=', ref),
                            ('external_referential_id',
                             '=', external_referential_id)],
                           context=context)
        if report:
            report_id = report[0]
        return report_id

    def _clean_successful_lines(self, cr, uid, report_id, context=None):
        lines_obj = self.pool.get('external.report.line')
        line_ids = lines_obj.search(cr, uid,
                                    [('external_report_id', '=', report_id),
                                    ('state', '=', 'success')],
                                    context=context)
        lines_obj.unlink(cr, uid, line_ids, context=context)
        return True

    def _retry_failed_lines(self, cr, uid, report_id, context=None):
        report = self.browse(cr, uid, report_id, context)
        for line in report.failed_line_ids:
            self.pool.get('external.report.line').retry(cr, uid, line.id, context)
        return True

    def start_report(self, cr, uid, id=None, ref=None,
                     external_referential_id=None, context=None):
        """ Start a report, use the report with the id in the parameter
        if given. Otherwise, try to find the report which have the same ref
         and external referential (we use the same report to avoid a
         multiplication of reports) If nothing is found, it create a new report
        """

        if not id and (not ref or not external_referential_id):
            raise Exception('No reference to create the report!')
        if id:
            report_id = id
        else:
            report_id = self.get_report_by_ref(cr, uid, ref,
                                               external_referential_id,
                                               context)

        log_cr = pooler.get_db(cr.dbname).cursor()
        try:
            if report_id:
                self.write(log_cr, uid, report_id,
                           {'start_date': time.strftime("%Y-%m-%d %H:%M:%S"),
                            'end_date': False},
                           context=context)

                # clean successful lines of the last report
                self._clean_successful_lines(log_cr, uid, report_id, context)
            else:
                report_id = self.create(log_cr, uid,
                                        # TODO get a correct name for the user
                                        {'name': ref,
                                         'ref': ref,
                                         'external_referential_id': external_referential_id,
                                         'start_date': time.strftime("%Y-%m-%d %H:%M:%S"),
                                         },
                                        context=context)
            log_cr.commit()

        finally:
            log_cr.close()

        self._retry_failed_lines(cr, uid, report_id, context)

        return report_id

    def end_report(self, cr, uid, id, context=None):
        """ Create history lines based on lines
        Successful lines are cleaned at each start of a report
        so we historize their aggregation.
        """

        lines_obj = self.pool.get('external.report.line')
        history_obj = self.pool.get('external.report.history')
        log_cr = pooler.get_db(cr.dbname).cursor()
        try:
            line_ids = lines_obj.search(log_cr, uid,
                                     [('external_report_id', '=', id)],
                                     context=context)

            grouped_lines = lines_obj.aggregate_actions(cr, uid,
                                                        line_ids,
                                                        context)

            for line in grouped_lines:
                history_obj.create(log_cr, uid,
                                   {
                        'external_report_id': id,
                        'res_model': line[1],
                        'action': line[2],
                        'count': grouped_lines[line],
                        'user_id': uid,
                        'state': line[0]
                    }, context=context)

            self.write(log_cr, uid, id,
                       {'end_date': time.strftime("%Y-%m-%d %H:%M:%S")},
                       context=context)

            log_cr.commit()
        finally:
            log_cr.close()
        return id

external_report()


class external_report_history(osv.osv):
    _name = 'external.report.history'
    _description = 'External Report History'
    _rec_name = 'external_report_id'
    _order = 'date desc'

    _columns = {
        'external_report_id': fields.many2one('external.report',
                                              'External Report',
                                              required=True,
                                              readonly=True,
                                              ondelete='cascade'),
        'date': fields.datetime('End Date', required=True, readonly=True),
        'res_model': fields.char('Resource Object', size=64,
                                 required=True, readonly=True),
        'action': fields.char('Action', size=64, required=True, readonly=True),
        'count': fields.integer('Count', readonly=True),
        'user_id': fields.many2one('res.users', 'User', required=True, readonly=True),
        'state': fields.selection((('success', 'Success'),
                                   ('fail', 'Failed')),
                                   'Status', required=True, readonly=True),
    }

    _defaults = {
        "date": lambda *a: time.strftime("%Y-%m-%d %H:%M:%S")
    }

external_report_history()


class external_report_lines(osv.osv):
    _name = 'external.report.line'
    _description = 'External Report Lines'
    _rec_name = 'res_id'
    _order = 'date desc'

    _columns = {
        'external_report_id': fields.many2one('external.report',
                                              'External Report',
                                              required=True,
                                              readonly=True,
                                              ondelete='restrict'),
        'state': fields.selection((('success', 'Success'),
                                   ('fail', 'Failed')),
                                   'Status', required=True, readonly=True),
        'res_model': fields.char('Resource Object', size=64,
                                 required=True, readonly=True),
        'res_id': fields.integer('Resource Id', readonly=True),
        'action': fields.char('Action', size=32, required=True, readonly=True),
        'date': fields.datetime('Date', required=True, readonly=True),
        'external_id': fields.char('External ID', size=64, readonly=True),
        'error_message': fields.text('Error Message', readonly=True),
        'origin_defaults': fields.text('Defaults', readonly=True),
        'origin_context': fields.text('Context', readonly=True),
    }

    _defaults = {
        "date": lambda *a: time.strftime("%Y-%m-%d %H:%M:%S")
    }

    def _log_base(self, cr, uid, state, model, action,
                 external_referential_id, res_id=None, external_id=None,
                 exception=None, defaults=None, context=None):
        defaults = defaults or {}
        context = context or {}

        existing_line_id = context.get('retry_report_line_id', False)

        # We do not log any action if no report is started
        # if the log was a fail, we raise to not let the import continue
        # This ensure a backward compatibility, synchro will continue to
        # work exactly the same way if no report is started
        if not(existing_line_id or context.get('external_report_id', False)):
            if state == 'fail':
                raise
            return False

        external_report_id = context['external_report_id']
        log_cr = pooler.get_db(cr.dbname).cursor()

        try:
            origin_defaults = defaults.copy()
            origin_context = context.copy()
            # connection object can not be kept in text indeed
            # FIXME : see if we have some problem with other objects
            # and maybe remove from the conect all objects
            # which are not string, boolean, list, dict, integer, float or ?
            del origin_context['conn_obj']
            if existing_line_id:
                self.write(log_cr, uid,
                               existing_line_id,
                               {'state': state,
                                'date': time.strftime("%Y-%m-%d %H:%M:%S"),
                                'error_message': exception and str(exception) or False,
                                'origin_defaults': str(origin_defaults),
                                'origin_context': str(origin_context),
                                })
            else:
                self.create(log_cr, uid, {
                                'external_report_id': external_report_id,
                                'state': state,
                                'res_model': model,
                                'action': action,
                                'external_referential_id': external_referential_id,
                                'date': time.strftime("%Y-%m-%d %H:%M:%S"),
                                'res_id': res_id,
                                'external_id': external_id,
                                'error_message': exception and str(exception) or False,
                                'origin_defaults': str(origin_defaults),
                                'origin_context': str(origin_context),
                            })

            log_cr.commit()

        finally:
            log_cr.close()
        return True

    def log_failed(self, cr, uid, model, action, external_referential_id,
                   res_id=None, external_id=None, exception=None,
                   defaults=None, context=None):
        return self._log_base(cr, uid, 'fail', model, action,
                             external_referential_id, res_id,
                             external_id, exception, defaults, context)

    def log_success(self, cr, uid, model, action, external_referential_id,
                    res_id=None, external_id=None, exception=None,
                    defaults=None, context=None):
        return self._log_base(cr, uid, 'success', model, action,
                             external_referential_id, res_id,
                             external_id, exception, defaults, context)

    def retry(self, cr, uid, ids, context=None):
        if isinstance(ids, int):
            ids = [ids]

        for log in self.browse(cr, uid, ids, context=context):
            origin_context = safe_eval(log.origin_context)
            origin_defaults = safe_eval(log.origin_defaults)

            # keep the id of the line to update it with the result
            origin_context['retry_report_line_id'] = log.id
            # force export of the resource
            origin_context['force_export'] = True
            origin_context['force'] = True
            # do not update "last export date"
            origin_context['do_not_update_date'] = True

            mapping = self.pool.get(log.res_model).\
            report_action_mapping(cr, uid, context=context)

            method = mapping.get(log.action, False)
            if not method:
                raise Exception("No python method defined for action %s" %
                                (log.action,))
            method(cr, uid,
                   log.res_id,
                   log.external_report_id.external_referential_id.id,
                   origin_defaults,
                   origin_context)

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

external_report_lines()
