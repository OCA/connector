# -*- coding: utf-8 -*-

import unittest2

import openerp
import openerp.tests.common as common
from openerp.addons.connector.session import (
        ConnectorSession,
        ConnectorSessionHandler)

DB = common.DB
ADMIN_USER_ID = common.ADMIN_USER_ID


class test_connector_session_handler(common.TransactionCase):
    """ Test ConnectorSessionHandler (without original cr and pool) """

    def setUp(self):
        super(test_connector_session_handler, self).setUp()
        self.context = {'lang': 'fr_FR'}
        self.session_hdl = ConnectorSessionHandler(
                DB, ADMIN_USER_ID,
                context=self.context)

    def test_empty_session(self):
        """
        Create a session without transaction
        """
        self.assertEqual(self.session_hdl.db_name, DB)
        self.assertEqual(self.session_hdl.uid, ADMIN_USER_ID)
        self.assertEqual(self.session_hdl.context, self.context)

    def test_with_session(self):
        """
        Create a session from the handler
        """
        with self.session_hdl.session() as session:
            pool = openerp.modules.registry.RegistryManager.get(DB)
            self.assertIsNotNone(session.cr)
            self.assertEqual(session.pool, pool)
            self.assertEqual(session.context, self.session_hdl.context)

    def test_with_session_cr(self):
        """
        Create a session from the handler and check if Cursor is usable.
        """
        with self.session_hdl.session() as session:
            session.cr.execute("SELECT id FROM res_users WHERE login=%s",
                               ('admin',))
            self.assertEqual(session.cr.fetchone(), (ADMIN_USER_ID,))

    def test_with_session_twice(self):
        """
        Check if 2 sessions can be opened on the same session
        """
        with self.session_hdl.session() as session:
            with self.session_hdl.session() as session2:
                self.assertNotEqual(session, session2)

class test_connector_session(common.TransactionCase):
    """ Test ConnectorSession """

    def setUp(self):
        super(test_connector_session, self).setUp()
        self.context = {'lang': 'fr_FR'}
        self.session = ConnectorSession(self.cr,
                                        self.uid,
                                        context=self.context)

    def test_change_user(self):
        """
        Change the user and check if it is reverted correctly at the end
        """
        original_uid = self.session.uid
        new_uid = 2
        with self.session.change_user(new_uid):
            self.assertEqual(self.session.uid, new_uid)
        self.assertEqual(self.session.uid, original_uid)

    def test_model_with_transaction(self):
        """
        Create a session with a model name, we should be able to access
        the model from a transaction
        """
        res_users = self.registry('res.users')

        self.assertEqual(self.session.pool.get('res.users'), res_users)
