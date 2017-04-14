# -*- coding: utf-8 -*-
# Author: Simone Orsi
# Copyright 2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from contextlib import contextmanager
from odoo.addons.connector.connector import ConnectorEnvironment
from odoo import models, fields, api, exceptions, _

BACKEND_VERSIONS = [
    ('1.0', 'Version 1.0'),
]


class ImportBackend(models.Model):
    _name = 'import.backend'
    _description = 'Import Backend'
    _inherit = 'connector.backend'
    _backend_type = 'import_backend'

    @contextmanager
    @api.multi
    def get_environment(self, model_name):
        self.ensure_one()
        yield ConnectorEnvironment(self, model_name)

    @api.model
    def _select_version(self):
        """ Available versions

        Can be inherited to add custom versions.
        """
        return BACKEND_VERSIONS

    @api.model
    def _select_interval_type(self):
        return [
            ('hours', 'Hours'),
            ('work_days', 'Work Days'),
            ('days', 'Days'),
            ('weeks', 'Weeks'),
            ('months', 'Months')
        ]

    version = fields.Selection(
        selection='_select_version',
        string='Version',
        required=True,
    )
    recordset_ids = fields.One2many(
        'import.recordset',
        'backend_id',
        string='Record Sets',
    )
    # cron stuff
    cron_mode = fields.Boolean('Cron mode?')
    cron_start_date = fields.Datetime(
        'Start date',
    )
    cron_interval_number = fields.Integer('Interval number')
    cron_interval_type = fields.Selection(
        selection='_select_interval_type',
        string='Interval type',
    )
    cron_id = fields.Many2one(
        'ir.cron',
        string='Related cron'
    )
    notes = fields.Text('Notes')
    debug_mode = fields.Boolean(
        'Debug mode?',
        help=_("Enabling debug mode causes the import to run "
               "in real time, without using any job queue. "
               "Make sure you don't do this in production!")
    )
    job_running = fields.Boolean(
        'Job running',
        compute='_compute_job_running',
        help=_("Tells you if a job is running for this backend."),
        readonly=True
    )
    enable_user_mode = fields.Boolean(
        'Enable user mode',
        default=True,
        help=_("Enabling user mode allows simple users "
               "to use the quick wizard for importing recordsets on demand.")
    )

    @api.model
    def get_cron_vals(self, backend=None):
        backend = backend or self
        return {
            'name': 'Cron for import backend %s' % backend.name,
            'model': backend._name,
            'function': 'run_all',
            'args': '(%s,)' % str(backend.id),
            'interval_number': backend.cron_interval_number,
            'interval_type': backend.cron_interval_type,
            'nextcall': backend.cron_start_date,
        }

    @api.model
    def create(self, vals):
        """ handle cron stuff
        """
        backend = super(ImportBackend, self).create(vals)
        if backend.cron_mode:
            cron_model = self.env['ir.cron']
            cron_vals = self.get_cron_vals(backend)
            cron = cron_model.create(cron_vals)
            backend.cron_id = cron.id
        return backend

    @api.multi
    def write(self, vals):
        """ handle cron stuff
        """
        res = super(ImportBackend, self).write(vals)
        for backend in self:
            if backend.cron_mode:
                # update related cron values
                cron_vals = self.get_cron_vals(backend)
                backend.cron_id.write(cron_vals)
        return res

    @api.multi
    def unlink(self):
        for item in self:
            item.check_delete()
        return super(ImportBackend, self).unlink()

    @api.model
    def check_delete(self):
        """ if debug mode is not ON check that we don't have
        any jobs related to our sub records.
        """
        if not self.debug_mode and self.job_running:
            raise exceptions.Warning(_('You must complete the job first!'))

    @api.multi
    def _compute_job_running(self):
        for item in self:
            running = False
            for recordset in self.recordset_ids:
                if recordset.has_job() and not recordset.job_done():
                    running = True
                    break
                for record in recordset.record_ids:
                    if record.has_job() and not record.job_done():
                        running = True
                        break
            item.job_running = running

    @api.model
    def run_all(self, backend_id=None):
        """ run all recordset imports
        """
        backend = backend_id and self.browse(backend_id) or self
        for recordset in backend.recordset_ids:
            recordset.run_import()

    @api.multi
    def button_complete_jobs(self):
        """ set all jobs to "completed" state.
        """
        self.ensure_one()
        for recordset in self.recordset_ids:
            for record in recordset.record_ids:
                if record.has_job() and not record.job_done():
                    record.job_id.button_done()
            if recordset.has_job() and not recordset.job_done():
                recordset.job_id.button_done()

    @api.onchange('enable_user_mode')
    def _onchange_enable_user_mode(self):
        """If user mode is enabled we want to run it with jobs by default."""
        self.debug_mode = not self.enable_user_mode
