# -*- coding: utf-8 -*-
# Copyright 2013-2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo.tests.common import TransactionCase
from odoo.addons.connector.connector import ConnectorEnvironment, Binder


class TestDefaultBinder(TransactionCase):
    """ Test the default binder implementation"""

    def setUp(self):
        super(TestDefaultBinder, self).setUp()

        self.backend_record = self.env['test.backend'].create(
            {'version': '1', 'name': 'Test'}
        )
        self.connector_env = ConnectorEnvironment(
            self.backend_record, 'connector.test.binding'
        )
        self.binder = self.connector_env.get_connector_unit(Binder)

    def test_default_binder(self):
        """ Small scenario with the default binder """
        test_record = self.env['connector.test.record'].create({})
        test_binding = self.env['connector.test.binding'].create({
            'backend_id': self.backend_record.id,
            'odoo_id': test_record.id,
        })

        # bind the test binding to external id = 99
        self.binder.bind(99, test_binding)
        # find the odoo binding bound to external record 99
        binding = self.binder.to_internal(99)
        self.assertEqual(binding, test_binding)
        # find the odoo record bound to external record 99
        record = self.binder.to_internal(99, unwrap=True)
        self.assertEqual(record, test_record)
        # find the external record bound to odoo binding
        external_id = self.binder.to_external(test_binding)
        self.assertEqual(external_id, 99)
        # find the external record bound to odoo record
        external_id = self.binder.to_external(test_record, wrap=True)
        self.assertEqual(external_id, 99)
        self.assertEqual(self.binder.unwrap_model(), 'connector.test.record')
        # unwrapping the binding should give the same binding
        self.assertEqual(self.binder.unwrap_binding(test_binding), test_record)
