# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2017 Camptocamp (<http://www.camptocamp.com>)
#
##############################################################################

from odoo import models, api, fields


class WizardImport(models.TransientModel):
    """ base class for wizard import
    """

    _name = 'wiz.connector.import.base'

    backend_id = fields.Many2one(
        string='Import type',
        comodel_name='import.backend',
        required=True,
        domain=[
            ('enable_user_mode', '=', True),
        ]
    )

    @api.multi
    def import_data(self):
        # import data
        self.prepare_import_data()
        # show confirmation popup
        view = self.env.ref('connector_importer.wizard_import_base')
        return {
            'view_type': 'form',
            'name': 'Import scheduled',
            'view_id': [view.id],
            'view_mode': 'form',
            'res_model': 'wiz.connector.import.base',
            'type': 'ir.actions.act_window',
            'target': 'new'
        }

    @api.multi
    def _prepare_import_data(self, area, available, prefix):
        recordset_model = self.env['import.recordset']
        for wiz in self:
            backend = wiz.backend_id
            for key in available:
                fname = key.replace(prefix, '')
                csv_file = getattr(self, fname, None)
                csv_filename = getattr(self, fname + '_filename', None)
                if csv_file:
                    values = {
                        'backend_id': backend.id,
                        'key': key,
                        'csv_file': csv_file,
                        'csv_filename': csv_filename,
                    }
                    recordset = recordset_model.sudo().create(values)
                    recordset.sudo().run_import()

    @api.multi
    def prepare_import_data(self):
        # this must raise attribute errors
        # if you don't implement proper attributes into your subclass
        self._prepare_import_data(self.AREA,
                                  self.AVAILABLE,
                                  self.PREFIX)
