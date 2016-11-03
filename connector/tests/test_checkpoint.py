# -*- coding: utf-8 -*-

import mock
from psycopg2 import IntegrityError

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

    def test_add_checkpoint_required_fields(self):
        with self.assertRaises(IntegrityError):
            self.env['connector.checkpoint'].create({
                'backend_id':
                    'connector.backend,' + str(self.backend_record.id),
            })

    def test_add_checkpoint_for_record(self):
        ckpoint = checkpoint.add_checkpoint(
            self.session, 'res.partner', self.partner.id,
            self.backend_record._name, self.backend_record.id)
        self.assertEqual(ckpoint.model_id.model, 'res.partner')
        self.assertEqual(ckpoint.record_id, self.partner.id)
        self.assertEqual(ckpoint.name, self.partner.display_name)
        self.assertEqual(ckpoint.backend_id.id, self.backend_record.id)
        self.assertTrue(ckpoint.message_follower_ids)

        # we can also provide a message
        msg = 'Check this out!'
        ckpoint_with_msg = checkpoint.add_checkpoint(
            self.session, 'res.partner', self.partner.id,
            self.backend_record._name, self.backend_record.id,
            message=msg)
        self.assertEqual(ckpoint_with_msg.message, msg)

    def test_add_checkpoint_for_message(self):
        msg = 'Oops, something went wrong, check this!'
        ckpoint = checkpoint.add_checkpoint_message(
            self.session, self.backend_record._name,
            self.backend_record.id, msg)
        self.assertFalse(ckpoint.model_id)
        self.assertFalse(ckpoint.record_id)
        self.assertEqual(ckpoint.name, msg)
        self.assertEqual(ckpoint.backend_id.id, self.backend_record.id)
        self.assertTrue(ckpoint.message_follower_ids)

    def test_add_checkpoint_from_backend(self):
        backend_record = self.env['connector.backend'].new({'name': 'Test'})
        # fake real id!
        backend_record._ids = [99, ]
        msg = "Yeah!"
        ckpoint = backend_record.add_checkpoint(
            model='res.partner', record_id=self.partner.id)
        self.assertEqual(ckpoint.model_id.model, 'res.partner')
        self.assertEqual(ckpoint.record_id, self.partner.id)
        self.assertEqual(ckpoint.name, self.partner.display_name)
        self.assertEqual(ckpoint.backend_id.id, 99)
        self.assertTrue(ckpoint.message_follower_ids)

        ckpoint = backend_record.add_checkpoint(message=msg)
        self.assertEqual(ckpoint.message, msg)
