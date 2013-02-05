# -*- coding: utf-8 -*-

import unittest2

import openerp
import openerp.tests.common as common
from openerp.addons.base_external_referentials.session import ConnectorSession

DB = common.DB
ADMIN_USER_ID = common.ADMIN_USER_ID


class test_connector_session(unittest2.TestCase):
    """ Try cr.execute with wrong parameters """

    def test_empty_session(self):
        """
        Create an session without transaction
        """
        context = {'lang': 'fr_FR'}
        session = ConnectorSession(DB, ADMIN_USER_ID)
        self.assertEqual(session.dbname, DB)
        self.assertEqual(session.uid, ADMIN_USER_ID)
        with self.assertRaises(AssertionError):
            session.cr
        with self.assertRaises(AssertionError):
            session.commit()
        with self.assertRaises(AssertionError):
            session.rollback()
        with self.assertRaises(AssertionError):
            session.close()

    def test_with_transaction(self):
        """
        Create a session and open a transaction context
        """
        session = ConnectorSession(DB, ADMIN_USER_ID)
        with session.transaction():
            self.assertIsNotNone(session.cr)
            self.assertIsNotNone(session.pool)
            with self.assertRaises(AssertionError):
                session.model
            session.cr.execute("SELECT id FROM res_users WHERE login=%s", ('admin',))
            self.assertEqual(session.cr.fetchone(), (ADMIN_USER_ID,))
        self.assertIsNone(session._cr)

    def test_with_transaction_twice(self):
        """
        Check if 2 transactions cannot be opened on the same session
        """
        session = ConnectorSession(DB, ADMIN_USER_ID)
        with session.transaction():
            with self.assertRaises(AssertionError):
                with session.transaction():
                    pass

    def test_change_user(self):
        """
        Change the user and check if it is reverted correctly at the end
        """
        session = ConnectorSession(DB, ADMIN_USER_ID)
        self.assertEqual(session.uid, ADMIN_USER_ID)
        new_uid = 2
        with session.change_user(new_uid):
            self.assertEqual(session.uid, new_uid)
        self.assertEqual(session.uid, ADMIN_USER_ID)

    def test_model_without_transaction(self):
        """
        Create a session with a model name, we should not be able to
        access the model without transaction (no pool)
        """
        session = ConnectorSession(DB, ADMIN_USER_ID, model_name='res.users')
        self.assertEqual(session.model_name, 'res.users')
        with self.assertRaises(AssertionError):
            session.model

    def test_copy_session_in_transaction(self):
        """
        Copy a session and check if the cr is not copied
        """
        import copy
        session = ConnectorSession(DB, ADMIN_USER_ID)
        with session.transaction():
            copy_session = copy.copy(session)
            self.assertIsNone(copy_session._cr)


class test_connector_session_transaction(common.TransactionCase):

    def test_model_with_transaction(self):
        """
        Create a session with a model name, we should be able to access
        the model from a transaction
        """
        res_users = self.registry('res.users')

        session = ConnectorSession(DB, ADMIN_USER_ID, model_name='res.users')
        self.assertEqual(session.model_name, 'res.users')
        with session.transaction():
            self.assertEqual(session.model, res_users)

    def test_use_existing_cr(self):
        """
        Use a session as a container for an existing cursor
        """
        session = ConnectorSession.use_existing_cr(self.cr,
                                                   self.uid,
                                                   self.registry)
        self.assertEqual(session.cr, self.cr)
        self.assertEqual(session.uid, self.uid)
        self.assertEqual(session.pool, self.registry)
        with self.assertRaises(AssertionError):
            with session.transaction():
                pass
