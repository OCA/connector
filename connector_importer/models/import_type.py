# -*- coding: utf-8 -*-
# Author: Simone Orsi
# Copyright 2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models, fields, api


class ImportType(models.Model):
    _name = 'import.type'
    _description = 'Import type'

    name = fields.Char(required=True)
    key = fields.Char(required=True)
    settings = fields.Text(
        string='Settings',
        required=True,
        help="""
            # comment me
            product.template:dotted.path.to.importer
            product.product:dotted.path.to.importer
            # another one
            product.supplierinfo:dotted.path.to.importer
        """
    )
    # TODO: provide default source and configuration policy
    # for an import type to ease bootstrapping recordsets from UI.
    # default_source_model_id = fields.Many2one()

    @api.multi
    def available_models(self):
        self.ensure_one()
        for line in self.settings.strip().splitlines():
            if line.strip() and not line.startswith('#'):
                model, importer = line.split(':')
                yield (model, importer)
