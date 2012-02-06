import time
import netsvc
import pooler
from osv import osv, fields
from tools.translate import _
from tools.safe_eval import safe_eval


class external_report(osv.osv):
    _name = 'external.report'
    _description = 'External Report'

#    def _count_failed_lines(self, cr, uid, ids, field_name, arg, context):
#        res = {}
#        for report in self.browse(cr, uid, ids, context):
#            res[id] = 0  # TODO count lines and define the store method
#            # search and count the returned ids
#        return res

    _columns = {
        'name': fields.char('Report Name', size=32, required=True,
                            readonly=True),
        'ref': fields.char('Report Reference', size=64, required=True,
                           readonly=True,
                           help="Internal reference which represents "
                                "the action like export catalog "
                                "or import orders"),
        'date': fields.datetime('Date', required=True, readonly=True),
        'external_referential_id': fields.many2one('external.referential',
                                                   'External Referential',
                                                   required=True,
                                                   readonly=True),
#        'fail_count': fields.function(_count_failed_lines,
#                                      type="integer", method=True,
#                                      string="Count of failed lines",
#                                      store=True),
        'line_ids': fields.one2many('external.report.line', 'external_report_id', 'Report Lines'),
        'history_ids': fields.one2many('external.report.history', 'external_report_id', 'History'),
    }

    _defaults = {
        "date": lambda *a: time.strftime("%Y-%m-%d %H:%M:%S")
    }


    def get_report_by_ref(self, cr, uid, ref, external_referential_id, context=None):
        report_id = False
        report = self.search(cr, uid,
                           [('ref', '=', ref),
                            ('external_referential_id', '=', external_referential_id)],
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

    def start_report(self, cr, uid, id=None, ref=None, external_referential_id=None, context=None):
        """ Start a report, use the report with the id in the parameter if given.
         Otherwise, try to find the report which have the same ref and external referential
         (we use the same report to avoid a multiplication of reports)
         If nothing is found, it create a new report
        """

        if not id and (not ref or not external_referential_id):
            raise osv.except_osv('Error', _('No reference to create the report!'))
        if id:
            report_id = id
        else:
            report_id = self.get_report_by_ref(cr, uid, ref, external_referential_id, context)

        log_cr = pooler.get_db(cr.dbname).cursor()

        try:
            if report_id:
                self.write(log_cr, uid, report_id,
                           {'date': time.strftime("%Y-%m-%d %H:%M:%S")},
                           context=context)

                # clean successful lines of the last report
                self._clean_successful_lines(log_cr, uid, report_id, context)
            else:
                report_id = self.create(log_cr, uid,
                                        {'name': ref,  # TODO get a correct name for the user
                                         'ref': ref,
                                         'external_referential_id': external_referential_id
                                         },
                                        context=context)
            log_cr.commit()

        finally:
            log_cr.close()

        return report_id

    def end_report(self, cr, uid, id, context=None):
        """ Create history lines based on lines
        Successful lines are cleaned at each start of a report
        so we historize their aggregation.
        """
        pass

external_report()


class external_report_history(osv.osv):
    _name = 'external.report.history'
    _description = 'External Report History'

    _columns = {
        'external_report_id': fields.many2one('external.report',
                                              'External Report',
                                              required=True,
                                              readonly=True),
        'timestamp': fields.datetime('Date', required=True, readonly=True),
        'res_model': fields.char('Resource Object', size=64,
                                 required=True, readonly=True),
        'method': fields.char('Method', size=64, required=True, readonly=True),
        'count': fields.integer('Count'),
        'user_id':fields.many2one('res.users', 'User', required=True, readonly=True),
        'state': fields.selection((('success', 'Success'),
                                   ('fail', 'Failed')),
                                   'Status', required=True, readonly=True),
    }

    _defaults = {
        "timestamp": lambda *a: time.strftime("%Y-%m-%d %H:%M:%S")
    }

external_report_history()


class external_report_lines(osv.osv):
    _name = 'external.report.line'
    _description = 'External Report Lines'
    _rec_name = 'res_id'

    METHOD_EXPORT = 'export'
    METHOD_IMPORT = 'import'

    def method_mapping(self, cr, uid, context=None):
        """Returns the name of the method on the object to use.
         Inherit it in your modules to add you owns
        """
        mapping = {
            self.METHOD_EXPORT: 'retry_export',
            self.METHOD_IMPORT: 'retry_import',
        }
        return mapping

    def _method_selection(self, cr, uid, context=None):
        mapping = self.method_mapping(cr, uid, context)
        return zip(mapping.keys(), mapping.keys())

    _columns = {
        'external_report_id': fields.many2one('external.report',
                                              'External Report',
                                              required=True,
                                              readonly=True),
        'state': fields.selection((('success', 'Success'),
                                   ('fail', 'Failed')),
                                   'Status', required=True, readonly=True),
        'res_model': fields.char('Resource Object', size=64,
                                 required=True, readonly=True),
        'res_id': fields.integer('Resource Id', readonly=True),
        'method': fields.selection(_method_selection,
                                    'Method', required=True, readonly=True),
        'timestamp': fields.datetime('Date', required=True, readonly=True),
        'external_id': fields.char('External ID', size=64, readonly=True),
        'error_message': fields.text('Error Message', readonly=True),
        'origin_defaults': fields.text('Defaults', readonly=True),
        'origin_context': fields.text('Context', readonly=True),
    }

    _defaults = {
        "timestamp": lambda *a: time.strftime("%Y-%m-%d %H:%M:%S")
    }
    _order = "timestamp desc"

    def _log_base(self, cr, uid, state, model, method,
                 external_referential_id, res_id=None, external_id=None,
                 exception=None, defaults=None, context=None):
        defaults = defaults or {}
        context = context or {}

        existing_line_id = context.get('retry_from_log_id', False)

        # we do not log any action if no report is started
        # if the log was a fail, we raise to not let the import continue
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
                               context['retry_from_log_id'],
                               {'state': state,
                                'timestamp': time.strftime("%Y-%m-%d %H:%M:%S"),
                                'error_message': exception and str(exception) or False,
                                'origin_defaults': str(origin_defaults),
                                'origin_context': str(origin_context),
                                })
            else:
                self.create(log_cr, uid, {
                                'external_report_id' : external_report_id,
                                'state': state,
                                'res_model': model,
                                'method': method,
                                'external_referential_id': external_referential_id,
                                'timestamp': time.strftime("%Y-%m-%d %H:%M:%S"),
                                'res_id': res_id,
                                'external_id': external_id,
                                'error_message': exception and str(exception) or False,
                                'origin_defaults': str(origin_defaults),
                                'origin_context': str(origin_context),
                            })

            log_cr.commit()

            if context.get('retry_from_log_id', False):
                del context['retry_from_log_id']
        finally:
            log_cr.close()
        return True

    def log_failed(self, cr, uid, model, method, external_referential_id,
                   res_id=None, external_id=None, exception=None,
                   defaults=None, context=None):
        return self._log_base(cr, uid, 'fail', model, method,
                             external_referential_id, res_id,
                             external_id, exception, defaults, context)

    def log_success(self, cr, uid, model, method, external_referential_id,
                    res_id=None, external_id=None, exception=None,
                    defaults=None, context=None):
        return self._log_base(cr, uid, 'success', model, method,
                             external_referential_id, res_id,
                             external_id, exception, defaults, context)

    def execute(self, cr, uid, ids, context=None):
        if isinstance(ids, int):
            ids = [ids]

        for log in self.browse(cr, uid, ids, context=context):
            origin_context = safe_eval(log.origin_context)
            origin_context['retry_from_log_id'] = log.id
            origin_context['force_export'] = True
            origin_context['force'] = True  # force export of the resource
            origin_defaults = safe_eval(log.origin_defaults)

            mapping = self.method_mapping(cr, uid, context=context)
            if not mapping.get(log.method, False):
                raise Exception("No python method defined to execute %s" % (log.method,))

            method = eval('self.pool.get(log.res_model).' + mapping[log.method])
            method(cr, uid,
                   log.res_id,
                   log.external_report_id.external_referential_id.id,
                   origin_defaults,
                   origin_context)
        return True

external_report_lines()
