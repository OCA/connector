# -*- coding: utf-8 -*-
# Copyright 2016 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import api, fields, models
from odoo.addons.queue_job.job import job, related_action


class TestBackend(models.Model):

    _name = 'test.backend'
    _inherit = ['connector.backend']

    @property
    def _backend_type(self):
        # this is a hack for the tests:
        # the related_action_unwrap_binding uses the
        # _backend_type to know if we are using old
        # ConnectorUnit or the new Components, because the _backend_type
        # is used only by the ConnectorUnit system.
        # As we want to test both, we pass this key in the ConnectorUnit
        # tests context
        if self.env.context.get('test_connector_units'):
            return 'test_connector'

    # useless for components
    version = fields.Selection(
        selection=[('1', '1')],
        string='Version',
        required=True,
    )


class ConnectorTestRecord(models.Model):
    _name = 'connector.test.record'


class ConnectorTestBinding(models.Model):
    _name = 'connector.test.binding'
    _inherit = 'external.binding'
    _inherits = {'connector.test.record': 'odoo_id'}

    backend_id = fields.Many2one(
        comodel_name='test.backend',
        string='Backend',
        required=True,
        ondelete='restrict',
    )
    external_id = fields.Integer(string='ID on External')
    odoo_id = fields.Many2one(comodel_name='connector.test.record',
                              string='Test Record',
                              required=True,
                              index=True,
                              ondelete='restrict')

    _sql_constraints = [
        ('test_binding_uniq', 'unique(backend_id, external_id)',
         "A binding already exists for this record"),
    ]

    @job
    @related_action(action='related_action_unwrap_binding')
    @api.multi
    def job_related_action_unwrap(self):
        return self


class NoInheritsBinding(models.Model):

    _name = 'no.inherits.binding'
    _inherit = 'external.binding'

    backend_id = fields.Many2one(
        comodel_name='test.backend',
        string='Backend',
        required=True,
        ondelete='restrict',
    )
    external_id = fields.Integer(string='ID on External')
    _sql_constraints = [
        ('test_binding_uniq', 'unique(backend_id, external_id)',
         "A binding already exists for this record"),
    ]

    @job
    @related_action(action='related_action_unwrap_binding')
    @api.multi
    def job_related_action_unwrap(self):
        return self
