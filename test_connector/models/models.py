# Copyright 2016 Camptocamp SA
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html)

from odoo import fields, models


class TestBackend(models.Model):

    _name = "test.backend"
    _inherit = ["connector.backend"]
    _description = "Backends for testing Connector"


class ConnectorTestRecord(models.Model):
    _name = "connector.test.record"
    _description = "Records for testing Connector"


class ConnectorTestBinding(models.Model):
    _name = "connector.test.binding"
    _inherit = "external.binding"
    _inherits = {"connector.test.record": "odoo_id"}
    _description = "Bindings for testing Connector"

    backend_id = fields.Many2one(
        comodel_name="test.backend",
        string="Backend",
        required=True,
        ondelete="restrict",
    )
    external_id = fields.Integer(string="ID on External")
    odoo_id = fields.Many2one(
        comodel_name="connector.test.record",
        string="Test Record",
        required=True,
        index=True,
        ondelete="restrict",
    )

    _sql_constraints = [
        (
            "test_binding_uniq",
            "unique(backend_id, external_id)",
            "A binding already exists for this record",
        )
    ]

    def job_related_action_unwrap(self):
        return self


class NoInheritsBinding(models.Model):

    _name = "no.inherits.binding"
    _inherit = "external.binding"
    _description = "Bindings without inherit for testing Connector"

    backend_id = fields.Many2one(
        comodel_name="test.backend",
        string="Backend",
        required=True,
        ondelete="restrict",
    )
    external_id = fields.Integer(string="ID on External")
    _sql_constraints = [
        (
            "test_binding_uniq",
            "unique(backend_id, external_id)",
            "A binding already exists for this record",
        )
    ]

    def job_related_action_unwrap(self):
        return self
