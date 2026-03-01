# Copyright 2024 Kencove Farm Fence Supplies
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from unittest.mock import patch

from odoo.exceptions import UserError

from .common import OnshapeTestCase


class TestOnshapeBackend(OnshapeTestCase):
    def test_backend_creation(self):
        self.assertEqual(self.backend.state, "active")
        self.assertEqual(self.backend.auth_mode, "hmac")
        self.assertEqual(self.backend.base_url, "https://cad.onshape.com")

    def test_check_credentials_success(self):
        backend = self.env["onshape.backend"].create(
            {
                "name": "Draft Backend",
                "base_url": "https://cad.onshape.com",
                "auth_mode": "hmac",
                "api_key": "key",
                "api_secret": "secret",
                "state": "draft",
            }
        )
        with patch.object(
            type(self.env["onshape.backend"]),
            "_get_adapter",
        ) as mock_get:
            adapter = self._mock_adapter()
            mock_get.return_value = adapter
            backend.action_check_credentials()
            self.assertEqual(backend.state, "checked")

    def test_check_credentials_failure(self):
        backend = self.env["onshape.backend"].create(
            {
                "name": "Bad Backend",
                "base_url": "https://cad.onshape.com",
                "auth_mode": "hmac",
                "api_key": "bad_key",
                "api_secret": "bad_secret",
                "state": "draft",
            }
        )
        with patch.object(
            type(self.env["onshape.backend"]),
            "_get_adapter",
        ) as mock_get:
            adapter = self._mock_adapter()
            adapter.check_credentials.return_value = (False, "Unauthorized")
            mock_get.return_value = adapter
            with self.assertRaises(UserError):
                backend.action_check_credentials()

    def test_activate_requires_checked(self):
        backend = self.env["onshape.backend"].create(
            {
                "name": "Draft",
                "base_url": "https://cad.onshape.com",
                "auth_mode": "hmac",
                "api_key": "k",
                "api_secret": "s",
                "state": "draft",
            }
        )
        with self.assertRaises(UserError):
            backend.action_activate()

    def test_import_requires_active(self):
        backend = self.env["onshape.backend"].create(
            {
                "name": "Draft",
                "base_url": "https://cad.onshape.com",
                "auth_mode": "hmac",
                "api_key": "k",
                "api_secret": "s",
                "state": "draft",
            }
        )
        with self.assertRaises(UserError):
            backend.action_import_documents()

    def test_document_count(self):
        self.assertEqual(self.backend.document_count, 0)
        self._create_mock_document()
        self.backend.invalidate_recordset()
        self.assertEqual(self.backend.document_count, 1)

    def test_stat_button_actions(self):
        action = self.backend.action_open_documents()
        self.assertEqual(action["res_model"], "onshape.document")
        action = self.backend.action_open_product_bindings()
        self.assertEqual(action["res_model"], "onshape.product.product")
        action = self.backend.action_open_bom_bindings()
        self.assertEqual(action["res_model"], "onshape.mrp.bom")
