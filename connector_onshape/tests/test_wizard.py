# Copyright 2024 Kencove Farm Fence Supplies
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.exceptions import UserError

from .common import OnshapeTestCase


class TestImportWizard(OnshapeTestCase):
    def test_default_backend(self):
        wizard = self.env["onshape.import.wizard"].create({"import_type": "documents"})
        self.assertTrue(wizard.backend_id)
        self.assertEqual(wizard.backend_id.state, "active")

    def test_import_requires_active_backend(self):
        draft_backend = self.env["onshape.backend"].create(
            {
                "name": "Draft",
                "base_url": "https://cad.onshape.com",
                "auth_mode": "hmac",
                "api_key": "k",
                "api_secret": "s",
                "state": "draft",
            }
        )
        wizard = self.env["onshape.import.wizard"].create(
            {
                "backend_id": draft_backend.id,
                "import_type": "documents",
            }
        )
        with self.assertRaises(UserError):
            wizard.action_import()

    def test_documents_only_import(self):
        """Verify the wizard can be created for document import."""
        wizard = self.env["onshape.import.wizard"].create(
            {
                "backend_id": self.backend.id,
                "import_type": "documents",
            }
        )
        self.assertEqual(wizard.import_type, "documents")

    def test_auto_create_flag_propagation(self):
        self.backend.write({"auto_create_products": False})
        wizard = self.env["onshape.import.wizard"].create(
            {
                "backend_id": self.backend.id,
                "import_type": "products",
                "auto_create_products": True,
            }
        )
        self.assertTrue(wizard.auto_create_products)
