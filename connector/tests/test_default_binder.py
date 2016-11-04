# -*- coding: utf-8 -*-

import mock
from odoo.tests.common import TransactionCase
from odoo.addons.connector.connector import ConnectorEnvironment
from odoo.addons.connector.session import ConnectorSession
from odoo.addons.connector.connector import Binder
from odoo.addons.connector.backend import Backend


class TestDefaultBinder(TransactionCase):
    """ Test the default binder implementation"""

    def setUp(self):
        super(TestDefaultBinder, self).setUp()

        class PartnerBinder(Binder):
            "we use already existing fields for the binding"
            _model_name = 'res.partner'
            _external_field = 'ref'
            _sync_date_field = 'date'
            _backend_field = 'color'
            _odoo_field = 'id'

        self.session = ConnectorSession(self.cr, self.uid)
        self.backend = Backend('dummy', version='1.0')
        backend_record = mock.Mock()
        backend_record.id = 1
        backend_record.get_backend.return_value = self.backend
        self.connector_env = ConnectorEnvironment(
            backend_record, self.session, 'res.partner')
        self.partner_binder = PartnerBinder(self.connector_env)

    def test_default_binder(self):
        """ Small scenario with the default binder """
        partner = self.env.ref('base.main_partner')
        partner.write({'color': 1})
        # bind the main partner to external id = 0
        self.partner_binder.bind(0, partner.id)
        # find the odoo partner bound to external partner 0
        odoo_id = self.partner_binder.to_odoo(0)
        self.assertEqual(odoo_id, partner.id)
        odoo_id = self.partner_binder.to_odoo(0)
        self.assertEqual(odoo_id.id, partner.id)
        odoo_id = self.partner_binder.to_odoo(0, unwrap=True)
        self.assertEqual(odoo_id, partner.id)
        # find the external partner bound to odoo partner 1
        external_id = self.partner_binder.to_backend(partner.id)
        self.assertEqual(external_id, '0')
        external_id = self.partner_binder.to_backend(partner.id, wrap=True)
        self.assertEqual(external_id, '0')
        # unwrap model should be None since we set 'id' as the _odoo_field
        self.assertEqual(self.partner_binder.unwrap_model(), None)
        # unwrapping the binding should give the same binding
        self.assertEqual(self.partner_binder.unwrap_binding(1), 1)
