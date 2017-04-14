# -*- coding: utf-8 -*-
# Author: Simone Orsi
# Copyright 2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models, fields, api

from ..utils.importer_utils import gen_chunks, CSVReader


# TODO: Alex suggests to make `import.source.*` model `inherit+s`
# from `import.source`. Then on the recordset
# we'll have a `source_model_id` field where you can select
# which kind of source you want to use.
# Developers are supposed to provide an override for the recordset view
# to display a source tab  based on the selected model.
# Alternatively we can use a generic Reference field to attache the source
# to the recordset but we should provide a button+wizard
# to allow users to edit the source and create/edit in on the fly
# under the hood.


class ImportSource(models.AbstractModel):
    _name = 'import.source.mixin'
    _description = 'Import source mixin'
    # TODO: use this to generate a name
    _source_type = ''

    chunk_size = fields.Integer(
        required=True,
        default=500,
        string='Chunks Size'
    )

    @api.multi
    def get_lines(self):
        self.ensure_one()
        # retrieve lines
        lines = self._get_lines()

        # sort them
        lines_sorted = self._sort_lines(lines)

        for i, chunk in enumerate(gen_chunks(lines_sorted,
                                  chunksize=self.chunk_size)):
            # get out of chunk iterator
            yield list(lines)

    def _get_lines(self):
        raise NotImplementedError()

    def _sort_lines(self, lines):
        return lines


# TODO: this must be a Model and inherits from source mixin.
class CSVSource(models.AbstractModel):
    _name = 'import.source.csv'
    _inherit = 'import.source.mixin'
    _description = 'CSV import source'
    _source_type = 'csv'

    csv_file = fields.Binary('CSV file')
    # use these to load file from an FS path
    csv_filename = fields.Char('CSV filename')
    csv_path = fields.Char('CSV path')
    csv_delimiter = fields.Char(
        string='CSV delimiter',
        default=';',
    )

    def _get_lines(self):
        # read CSV
        reader_args = {
            'delimiter': self.csv_delimiter,
        }
        if self.csv_path:
            # TODO: join w/ filename
            reader_args['filepath'] = self.csv_path
        else:
            reader_args['filedata'] = self.csv_file

        reader = CSVReader(**reader_args)
        return reader.read_lines()
