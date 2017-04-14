# -*- coding: utf-8 -*-
# Author: Simone Orsi
# Copyright 2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo.addons.connector.unit.synchronizer import Importer

from ..backends import import_backend
from ..log import logger
from ..events import chunk_finished_event

import os
import datetime
import pprint
pp = pprint.PrettyPrinter(indent=4)


@import_backend
class BaseImporter(Importer):
    _model_name = ''


@import_backend
class RecordSetImporter(BaseImporter):
    """Base importer for recordsets."""

    _model_name = 'import.recordset'

    def run(self, recordset, **kw):
        # update recordset report
        now = datetime.datetime.now().strftime('%d/%m/%Y %H:%M')
        recordset.set_report({
            'last_start': now,
        })
        msg = 'START RECORDSET {0}({1})'.format(recordset.name,
                                                recordset.id)
        logger.info(msg)

        record_model = recordset.record_ids

        # read CSV
        # TODO: when we solve the issue of source relation on recordset
        # this will be something like:
        # source = recordset.get_source()
        # source.get_lines()
        for chunk in recordset.get_lines():
            # create chuncked records and run their imports
            record = record_model.create({'recordset_id': recordset.id})
            # store data
            record.set_data(chunk)
            record.run_import()


@import_backend
class RecordImporter(BaseImporter):
    """Base importer for records."""

    # _base_mapper = ''
    _model_name = ''
    unique_key = ''
    # log and report errors
    # do not make the whole import fail
    _break_on_error = True
    # flush existing report on each run for the same recordset
    _report_flush = True

    def _init(self, record):
        self.record = record
        self.recordset = record.recordset_id
        self.backend = self.recordset.backend_id
        self._final_chunk_report = {
            'created': 0,
            'updated': 0,
            'skipped': 0,
            'errors': 0
        }
        self._skipped = []
        self._errors = []
        self._log_prefix = self.recordset.import_type_id.key + ' '
        self._logger = logger

    def find_domain(self, values, orig_values):
        return [(self.unique_key, '=', values[self.unique_key])]

    def find(self, values, orig_values):
        """Find any existing item."""
        items = self.model.search(
            self.find_domain(values, orig_values), order='create_date desc')
        return items and items[0] or []

    def exists(self, values, orig_values):
        """Return true if the items exists."""
        return bool(self.find(values, orig_values))

    def skip_it(self, values, orig_values):
        """Skip item import conditionally... if you want ;).

        You can return back `False` to not skip
        or a dictionary containing info about skip reason.
        """
        if self.exists(values, orig_values) \
                and not self.recordset.override_existing:
            msg = 'ALREADY EXISTS'
            if self.unique_key:
                msg += ': {}={}'.format(
                    self.unique_key, values[self.unique_key])
            return {
                'message': msg,
                'odoo_record': self.find(values, orig_values).id,
            }
        return False

    def pre_create(self, values, orig_values):
        """Do some extra stuff before creating a missing object."""
        pass

    def post_create(self, odoo_record, values, orig_values):
        """Do some extra stuff after creating a missing object."""
        pass

    def create_context(self):
        """Inject context variables on create."""
        return {}

    def create(self, values, orig_values):
        """Create a new odoo record."""
        self.pre_create(values, orig_values)
        record = self.model.with_context(self.create_context()).create(values)
        self.post_create(record, values, orig_values)
        return record

    def pre_write(self, values, orig_values):
        """Do some extra stuff before updating an existing object."""
        pass

    def post_write(self, odoo_record, values, orig_values):
        """Do some extra stuff after updating an existing object."""
        pass

    def write_context(self):
        """Inject context variables on write."""
        return {}

    def write(self, values, orig_values):
        """Update an existing odoo record."""
        # TODO: add a checkpoint? log something?
        odoo_record = self.find(values, orig_values)
        self.pre_write(values, orig_values)
        odoo_record.with_context(self.write_context()).write(values)
        self.post_write(odoo_record, values, orig_values)
        return odoo_record

    def cleanup_line(self, line):
        """Apply basic cleanup on lines."""
        # we cannot alter dict keys while iterating
        res = {}
        for k, v in line.iteritems():
            if not k.startswith('_'):
                k = self.clean_line_key(k)
            if isinstance(v, basestring):
                v = v.strip()
            res[k] = v
        return res

    def clean_line_key(self, key):
        """Clean record key.

        Sometimes your CSV source do not have proper keys,
        they can contain a lot of crap or they can change
        lower/uppercase from import to import.
        You can override this method to normalize keys
        and make your import mappers work reliably.
        """
        return key.strip()

    def verbose_log(self, line, values):
        """Handle verbose log."""
        if os.environ.get('IMPORTER_DEBUG_MODE_VERBOSE'):
            # more verbosity if debug mode on
            print '#' * 100
            pp.pprint(line)
            # print line
            print '-' * 100
            pp.pprint(values)
            # print values
            print '#' * 100

    def prepare_line(self, line):
        """Pre-manipulate a line if needed."""
        pass

    def _log(self, msg, line=None, level='info'):
        handler = getattr(self._logger, level)
        msg = '{prefix}{line}[model: {model}] {msg}'.format(
            prefix=self._log_prefix,
            line='[line: {}]'.format(line['_line_nr']) if line else '',
            model=self._model_name,
            msg=msg
        )
        handler(msg)

    def _error_info(self, line, odoo_record=None, err=''):
        return {
            'line': line['_line_nr'],
            'reason': err,
            'model': self._model_name,
            'odoo_record': odoo_record and odoo_record.id or None,
        }

    def _log_updated(self, values, line, odoo_record, err=''):
        self._log('UPDATED [id: {}]'.format(odoo_record.id), line=line)
        self._final_chunk_report['updated'] += 1

    def _log_error(self, values, line, odoo_record, err=''):
        self._final_chunk_report['errors'] += 1
        if err:
            self._errors.append(self._error_info(line, err=err))

    def _log_created(self, values, line, odoo_record, err=''):
        self._log('CREATED [id: {}]'.format(odoo_record.id), line=line)
        self._final_chunk_report['created'] += 1

    def _skipped_info(self, line, skip_info):
        info = {
            'line': line['_line_nr'],
            'model': self._model_name,
        }
        info.update(skip_info or {})
        return info

    def _log_skipped(self, values, line, skip_info):
        # `skip_it` could contain a msg
        self._log('SKIPPED ' + skip_info.get('message'),
                  line=line, level='warn')
        self._final_chunk_report['skipped'] += 1
        self._skipped.append(self._skipped_info(line, skip_info))

    def _do_report(self):
        recordset = self.record.recordset_id
        report = recordset.get_report() if self._report_flush else {}
        # update last global report
        default_report = {}.fromkeys(self._final_chunk_report.keys(), 0)
        last_summary = report.get('last_summary', default_report)
        for k, v in self._final_chunk_report.iteritems():
            last_summary[k] += v
        report['last_summary'] = last_summary
        report['skipped'] = report.get('skipped', []) + self._skipped
        report['errors'] = report.get('errors', []) + self._errors
        recordset.set_report(report)

    def _record_lines(self):
        """Retrive lines to import from record.

        You can use this to inject/remove lines on demand.
        """
        return self.record.get_data()

    def run(self, record, **kw):
        """Run the import machinery."""

        if not record:
            # TODO: maybe deleted -> should we handle this better?
            msg = 'NO RECORD FOUND, maybe deleted? Check your jobs!'
            logger.error(msg)
            return

        self._init(record)

        for line in self._record_lines():
            line = self.cleanup_line(line)
            self.prepare_line(line)
            values = self.mapper.map_record(line).values()
            self.verbose_log(line, values)

            # handle forced skipping
            skip_info = self.skip_it(values, line)
            if skip_info:
                self._log_skipped(values, line, skip_info)
                continue

            if self.exists(values, line):
                # update
                try:
                    odoo_record = self.write(values, line)
                    err = ''
                except Exception as err:
                    # TODO: track reason (log + checkpoint)
                    if self._break_on_error:
                        raise
                    odoo_record = None
                if odoo_record:
                    self._log_updated(values, line, odoo_record)
                else:
                    self._log_error(values, line, odoo_record, err=err)
            else:
                try:
                    odoo_record = self.create(values, line)
                    err = ''
                except Exception as err:
                    # TODO: track reason (log + checkpoint)
                    if self._break_on_error:
                        raise
                    odoo_record = None
                if odoo_record:
                    self._log_created(values, line, odoo_record)
                else:
                    self._log_error(values, line, odoo_record, err=err)

                # XXX: should we store a reference to created obj
                # inot import.record item?

        # update report
        self._do_report()

        # log chunk finished
        msg = ' '.join([
            'CHUNK FINISHED',
            '[created: {created}]',
            '[updated: {updated}]',
            '[skipped: {skipped}]',
            '[errors: {errors}]',
        ]).format(**self._final_chunk_report)
        self._log(msg)

        # TODO
        # chunk_finished_event.fire(
        #     self.env, self.record.id, self.model._name)
        self.after_all()

    def after_all(self, *args):
        """Get something done after all the children jobs have completed."""
        pass
