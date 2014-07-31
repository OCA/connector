# -*- coding: utf-8 -*-

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
        res_users = self.registry('res.users').search_count(self.cr,
                                                            self.uid,
                                                            [])
        sess_res_users_obj = self.session.pool.get('res.users')
        sess_res_users = sess_res_users_obj.search_count(self.cr,
                                                         self.uid,
                                                         [])
        self.assertEqual(sess_res_users, res_users)

    def test_change_context(self):
        """
        Change the context and check if it is reverted correctly at the end
        """
        test_key = 'test_key'
        self.assertNotIn(test_key, self.session.context)
        with self.session.change_context({test_key: 'value'}):
            self.assertIn(test_key, self.session.context)
        self.assertNotIn(test_key, self.session.context)

        # change the context on a session not initialized with a context
        session = ConnectorSession(self.cr, self.uid)
        with session.change_context({test_key: 'value'}):
            self.assertIn(test_key, session.context)
        self.assertNotIn(test_key, session.context)
