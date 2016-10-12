# -*- coding: utf-8 -*-

import mock
import openerp.tests.common as common

from openerp.addons.connector.session import (
    ConnectorSession,
)
from openerp.addons.connector.backend import Backend
from openerp.addons.connector.checkpoint import checkpoint


class TestCheckpoint(common.TransactionCase):

    def setUp(self):
        super(TestCheckpoint, self).setUp()
        self.session = ConnectorSession(self.cr, self.uid)
        self.backend = Backend('dummy', version='1.0')
        self.backend_record = mock.Mock()
        self.backend_record._name = 'connector.backend'
        self.backend_record.id = 1
        self.backend_record.get_backend.return_value = self.backend
        self.partner = self.env.ref('base.main_partner')

    def test_add_checkpoint_for_record(self):
        ckpoint = checkpoint.add_checkpoint(
            self.session, 'res.partner', self.partner.id,
            self.backend_record._name, self.backend_record.id)
        self.assertEqual(ckpoint.model_id.model, 'res.partner')
        self.assertEqual(ckpoint.record_id, self.partner.id)
        self.assertEqual(ckpoint.name, self.partner.display_name)
        self.assertEqual(ckpoint.backend_id.id, self.backend_record.id)
        self.assertTrue(ckpoint.message_follower_ids)
