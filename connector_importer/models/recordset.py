# -*- coding: utf-8 -*-
# Author: Simone Orsi
# Copyright 2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import json
import os

from odoo import models, fields, api
from odoo.addons.connector.unit.synchronizer import Importer
from odoo.addons.queue_job.job import (
    DONE, PENDING, FAILED, STATES, job)

from .job_mixin import JobRelatedMixin
from ..log import logger
from ..utils.report_html import Reporter
from ..utils.misc import import_klass_from_dotted_path


def get_record_importer(env, importer_dotted_path=None):
    if importer_dotted_path is None:
        return env.get_connector_unit(Importer)
    if not importer_dotted_path.startswith('odoo.addons.'):
        importer_dotted_path = 'odoo.addons.' + importer_dotted_path
    return env.get_connector_unit(
        import_klass_from_dotted_path(importer_dotted_path))


class ImportRecordSet(models.Model, JobRelatedMixin):
    _name = 'import.recordset'
    # TODO: temporary inherit!
    # `import.source.*` model should have a dynamic relation
    # with the recordset so that we can easily define new source types
    # and attach them to the recordset on the fly via UI.
    # Unfortunately the `fields.Reference` field sucks
    # especially if you want to create new records on the fly.
    # We need a better solution for this.
    _inherit = 'import.source.csv'
    _description = 'Import recordset'
    _order = 'sequence ASC, create_date DESC'
    _backend_type = 'import_backend'

    backend_id = fields.Many2one(
        'import.backend',
        string='Import Backend'
    )
    sequence = fields.Integer(
        'Sequence',
        help="Sequence for the handle.",
        default=10
    )
    import_type_id = fields.Many2one(
        string='Import type',
        comodel_name='import.type',
        required=True,
    )
    override_existing = fields.Boolean(
        string='Override existing items',
        default=True,
    )
    name = fields.Char(
        string='Name',
        compute='_compute_name',
    )
    create_date = fields.Datetime(
        'Create date',
    )
    record_ids = fields.One2many(
        'import.record',
        'recordset_id',
        string='Records',
    )
    # store info about imports report
    jsondata = fields.Text('JSON Data')
    report_html = fields.Html(
        'Report summary', compute='_compute_report_html')
    full_report_url = fields.Char(
        'Full report url', compute='_compute_full_report_url')
    jobs_global_state = fields.Selection(
        string='Jobs global state',
        selection=STATES,
        compute='_compute_jobs_global_state',
        help=(
            "Tells you if a job is running for this recordset. "
            "If any of the sub jobs is not DONE or FAILED "
            "we assume the global state is PENDING."
        ),
        readonly=True
    )

    @api.multi
    def unlink(self):
        # inheritance of non-model mixin - like JobRelatedMixin -
        # does not work w/out this
        return super(ImportRecordSet, self).unlink()

    @api.one
    @api.depends('backend_id.name')
    def _compute_name(self):
        names = [
            self.backend_id.name,
            '#' + str(self.id),
        ]
        self.name = ' '.join(filter(None, names))

    @api.multi
    def set_report(self, values):
        """ update import report values
        """
        self.ensure_one()
        _values = self.get_report()
        _values.update(values)
        self.jsondata = json.dumps(_values)

    @api.model
    def get_report(self):
        return json.loads(self.jsondata or '{}')

    @api.depends('jsondata')
    def _compute_report_html(self):
        for item in self:
            if not item.jsondata:
                continue
            reporter = Reporter(item.jsondata, full_url=item.full_report_url)
            item.report_html = reporter.html()

    @api.multi
    def _compute_full_report_url(self):
        for item in self:
            item.full_report_url = \
                '/importer/import-recordset/{}'.format(item.id)

    def debug_mode(self):
        return self.backend_id.debug_mode or \
            os.environ.get('IMPORTER_DEBUG_MODE')

    @api.multi
    def _compute_jobs_global_state(self):
        for item in self:
            item.jobs_global_state = item._get_global_state()

    @api.model
    def _get_global_state(self):
        done = True
        for item in self.record_ids:
            if item.job_state not in (DONE, FAILED):
                done = False
                break
        if not done:
            # we assume that if not all the jobs are done
            # or failed we stay PENDING
            return PENDING
        return DONE

    @api.multi
    @job
    def import_recordset(self):
        """This job will import a recordset."""
        with self.backend_id.get_environment(self._name) as env:
            importer = env.get_connector_unit(Importer)
            return importer.run(self)

    @api.multi
    def run_import(self):
        """ queue a job for creating records (import.record items)
        """
        job_method = self.with_delay().import_recordset
        if self.debug_mode():
            logger.warn('### DEBUG MODE ACTIVE: WILL NOT USE QUEUE ###')
            job_method = self.import_recordset

        for item in self:
            job = job_method()
            if job:
                # link the job
                item.write({'job_id': job.id})
            if self.debug_mode():
                # debug mode, no job here: reset it!
                item.write({'job_id': False})
        if self.debug_mode():
            # TODO: port this
            # # the "after_all" job needs to be fired manually when in debug mode
            # # since the event handler in .events.chunk_finished_subscriber
            # # cannot estimate when all the chunks have been processed.
            # for model, importer in self.import_type_id.available_models():
            #     import_record_after_all(
            #         session,
            #         self.backend_id.id,
            #         model,
            #     )
            pass


# TODO
# @job
# def import_record_after_all(
#         session, backend_id, model_name, last_record_id=None, **kw):
#     """This job will import a record."""
#     # TODO: check this
#     model = 'import.record'
#     env = get_environment(session, model, backend_id)
#     # recordset = None
#     # if last_record_id:
#     #     record = env[model].browse(last_record_id)
#     #     recordset = record.recordset_id
#     importer = get_record_importer(env)
#     return importer.after_all()


class ImportRecord(models.Model, JobRelatedMixin):
    _name = 'import.record'
    _description = 'Import record'
    _order = 'date DESC'
    _backend_type = 'import_backend'

    date = fields.Datetime(
        'Import date',
        default=fields.Date.context_today,
    )
    jsondata = fields.Text('JSON Data')
    recordset_id = fields.Many2one(
        'import.recordset',
        string='Recordset'
    )
    backend_id = fields.Many2one(
        'import.backend',
        string='Backend',
        related='recordset_id.backend_id',
        readonly=True,
    )

    @api.multi
    def unlink(self):
        # inheritance of non-model mixin does not work w/out this
        return super(ImportRecord, self).unlink()

    @api.multi
    @api.depends('date')
    def _compute_name(self):
        for item in self:
            names = [
                item.date,
            ]
            item.name = ' / '.join(filter(None, names))

    @api.multi
    def set_data(self, adict):
        self.ensure_one()
        self.jsondata = json.dumps(adict)

    @api.multi
    def get_data(self):
        self.ensure_one()
        return json.loads(self.jsondata or '{}')

    @api.multi
    def debug_mode(self):
        self.ensure_one()
        return self.backend_id.debug_mode or \
            os.environ.get('IMPORTER_DEBUG_MODE')

    @job
    def import_record(self, dest_model_name, importer_dotted_path=None, **kw):
        """This job will import a record."""

        with self.backend_id.get_environment(dest_model_name) as env:
            importer = get_record_importer(
                env, importer_dotted_path=importer_dotted_path)
            return importer.run(self)

    @api.multi
    def run_import(self):
        """ queue a job for importing data stored in to self
        """
        job_method = self.with_delay().import_record
        if self.debug_mode():
            logger.warn('### DEBUG MODE ACTIVE: WILL NOT USE QUEUE ###')
            job_method = self.import_record
        for item in self:
            import_type = item.recordset_id.import_type_id
            # we create a record and a job for each model name
            # that needs to be imported
            for model, importer in import_type.available_models():
                job = job_method(model, importer_dotted_path=importer)
                if job:
                    # link the job
                    item.write({'job_id': job.id})
                if self.debug_mode():
                    # debug mode, no job here: reset it!
                    item.write({'job_id': False})
