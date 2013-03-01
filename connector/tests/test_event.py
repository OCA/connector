# -*- coding: utf-8 -*-

import unittest2
import mock

from openerp.addons.connector.event import Event


class test_event(unittest2.TestCase):
    """ Test Event """

    def setUp(self):
        self.consumer1 = lambda session, model_name: None
        self.consumer2 = lambda session, model_name: None
        self.event = Event()

    def test_subscribe(self):
        self.event.subscribe(self.consumer1)
        self.assertIn(self.consumer1, self.event._consumers[None])

    def test_subscribe_decorator(self):
        @self.event
        def consumer():
            pass
        self.assertIn(consumer, self.event._consumers[None])

    def test_subscribe_model(self):
        self.event.subscribe(self.consumer1, model_names=['res.users'])
        self.assertIn(self.consumer1, self.event._consumers['res.users'])

    def test_subscribe_decorator_model(self):
        @self.event(model_names=['res.users'])
        def consumer():
            pass
        self.assertIn(consumer, self.event._consumers['res.users'])

    def test_unsubscribe(self):
        self.event.subscribe(self.consumer1)
        self.event.unsubscribe(self.consumer1)
        self.assertNotIn(self.consumer1, self.event._consumers[None])

    def test_unsubscribe_model(self):
        self.event.subscribe(self.consumer1, model_names=['res.users'])
        self.event.unsubscribe(self.consumer1, model_names=['res.users'])
        self.assertNotIn(self.consumer1, self.event._consumers['res.users'])

    def test_unsubscribe_not_existing(self):
        """ Discard without error """
        self.event.unsubscribe(self.consumer1)

    def test_unsubscribe_not_existing_model(self):
        """ Discard without error """
        self.event.unsubscribe(self.consumer1, model_names=['res.users'])

    def test_replacing(self):
        self.event.subscribe(self.consumer1)
        self.event.subscribe(self.consumer2, replacing=self.consumer1)
        self.assertNotIn(self.consumer1, self.event._consumers[None])
        self.assertIn(self.consumer2, self.event._consumers[None])

    def test_replacing_decorator(self):
        @self.event
        def consumer1(session, model_name):
            pass
        @self.event(replacing=consumer1)
        def consumer2(session, model_name):
            pass
        self.assertNotIn(consumer1, self.event._consumers[None])
        self.assertIn(consumer2, self.event._consumers[None])

    def test_replacing_model(self):
        self.event.subscribe(self.consumer1, model_names=['res.users'])
        self.event.subscribe(self.consumer2, replacing=self.consumer1,
                             model_names=['res.users'])
        self.assertNotIn(self.consumer1, self.event._consumers['res.users'])
        self.assertIn(self.consumer2, self.event._consumers['res.users'])

    def test_fire(self):
        class Recipient(object):
            def __init__(self):
                self.message = None
            def set_message(self, message):
                self.message = message

        @self.event
        def set_message(session, model_name, recipient, message):
            recipient.set_message(message)
        recipient = Recipient()
        # an event is fired on a model name
        session = mock.Mock()
        self.event.fire(session, 'res.users', recipient, 'success')
        self.assertEquals(recipient.message, 'success')

    def test_has_consumer_for(self):
        @self.event(model_names=['product.product'])
        def consumer1(session, model_name):
            pass
        self.assertTrue(self.event.has_consumer_for('product.product'))
        self.assertFalse(self.event.has_consumer_for('res.partner'))

    def test_has_consumer_for_global(self):
        @self.event
        def consumer1(session, model_name):
            pass
        self.assertTrue(self.event.has_consumer_for('product.product'))
        self.assertTrue(self.event.has_consumer_for('res.partner'))
