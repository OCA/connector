# -*- coding: utf-8 -*-

import unittest2
import mock

import openerp.tests.common as common
from openerp.addons.connector.event import (
        on_record_create,
        on_record_write,
        on_record_unlink
        )
from openerp.osv import orm


class test_connector_session(common.TransactionCase):
    """ Test ConnectorSession """

    def setUp(self):
        super(test_connector_session, self).setUp()
        class Recipient(object):
            pass
        self.recipient = Recipient()
        self.model = self.registry('res.partner')
        data_obj = self.registry('ir.model.data')
        self.partner_id = self.model.create(self.cr,
                                            self.uid,
                                            {'name': 'new'})

    def test_on_record_create(self):
        """
        Create a record and check if the event is called
        """
        @on_record_create
        def event(session, model_name, record_id):
            self.recipient.record_id = record_id

        record_id = self.model.create(self.cr,
                                      self.uid,
                                      {'name': 'Kif Kroker'})
        self.assertEqual(self.recipient.record_id, record_id)
        on_record_create.unsubscribe(event)

    def test_on_record_write(self):
        """
        Write on a record and check if the event is called
        """
        @on_record_write
        def event(session, model_name, record_id, fields=None):
            self.recipient.record_id = record_id
            self.recipient.fields = fields

        self.model.write(self.cr,
                         self.uid,
                         self.partner_id,
                         {'name': 'Lrrr',
                          'city': 'Omicron Persei 8'})
        self.assertEqual(self.recipient.record_id, self.partner_id)
        self.assertItemsEqual(self.recipient.fields, ['name', 'city'])
        on_record_write.unsubscribe(event)

    def test_on_record_unlink(self):
        """
        Unlink a record and check if the event is called
        """
        @on_record_unlink
        def event(session, model_name, record_id):
            if model_name == 'res.partner':
                self.recipient.record_id = record_id

        self.model.unlink(self.cr,
                          self.uid,
                          [self.partner_id])
        self.assertEqual(self.recipient.record_id, self.partner_id)
        on_record_write.unsubscribe(event)

    def test_on_record_write_no_consumer(self):
        """
        If no consumer is registered on the event for the model,
        the event should not be fired at all
        """
        with mock.patch.object(on_record_write, 'fire'):
            record_id = self.model.write(self.cr,
                                         self.uid,
                                         self.partner_id,
                                         {'name': 'Kif Kroker'})
            self.assertEqual(on_record_write.fire.called, False)
