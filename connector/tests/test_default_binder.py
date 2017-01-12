# -*- coding: utf-8 -*-
# Copyright 2013-2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import mock
from odoo.tests.common import TransactionCase
from odoo.addons.connector.connector import ConnectorEnvironment
from odoo.addons.connector.connector import Binder
from odoo.addons.connector.backend import Backend


class TestDefaultBinder(TransactionCase):
    """ Test the default binder implementation"""

    def setUp(self):
        super(TestDefaultBinder, self).setUp()

        # Let's pretend that res.users is the binding model
        # and res.partner is the record. We use this model
        # because it is an _inherits, so we can fake a
        # binding model without creating a new odoo addon
        class PartnerUserBinder(Binder):
            # we use already existing fields for the binding
            _model_name = 'res.users'
            _external_field = 'login'
            _sync_date_field = 'write_date'
            # pretend that company_id is our link to our
            # backend model (we don't have any backend model
            # so we fake it...)
            _backend_field = 'company_id'
            _odoo_field = 'partner_id'

        self.backend = Backend('dummy', version='1.0')
        backend_record = mock.Mock()
        self.backend_id = 1
        backend_record.id = self.backend_id
        backend_record.get_backend.return_value = self.backend
        self.connector_env = ConnectorEnvironment(
            backend_record, self.env, 'res.users')
        self.binder = PartnerUserBinder(self.connector_env)

    def test_default_binder(self):
        """ Small scenario with the default binder """
        user = self.env['res.users'].create(
            {'login': 'test', 'name': 'Test', 'company_id': self.backend_id}
        )
        partner = user.partner_id
        # bind the main partner to external id = 'test'
        self.binder.bind('test', partner)
        # find the odoo partner bound to external partner 'test'
        binding = self.binder.to_internal('test')
        self.assertEqual(binding, user)
        binding = self.binder.to_internal('test')
        self.assertEqual(binding, user)
        record = self.binder.to_internal('test', unwrap=True)
        self.assertEqual(record, partner)
        # find the external partner bound to odoo partner 1
        external_id = self.binder.to_external(user)
        self.assertEqual(external_id, 'test')
        external_id = self.binder.to_external(partner, wrap=True)
        self.assertEqual(external_id, 'test')
        self.assertEqual(self.binder.unwrap_model(), 'res.partner')
        # unwrapping the binding should give the same binding
        self.assertEqual(self.binder.unwrap_binding(user), partner)
