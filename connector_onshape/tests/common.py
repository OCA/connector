# Copyright 2024 Kencove Farm Fence Supplies
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from unittest.mock import MagicMock

from odoo.addons.component.tests.common import TransactionComponentCase

MOCK_DOCUMENT = {
    "id": "abc123def456abc123def456",
    "name": "Test Assembly",
    "defaultWorkspace": {"id": "ws_001"},
    "createdAt": "2024-01-01T00:00:00Z",
    "modifiedAt": "2024-06-01T12:00:00Z",
    "owner": {"name": "Test User"},
}

MOCK_DOCUMENTS_RESPONSE = {
    "items": [MOCK_DOCUMENT],
    "next": None,
}

MOCK_ELEMENTS = [
    {
        "id": "elem_ps_001",
        "name": "Part Studio 1",
        "elementType": "PARTSTUDIO",
        "microversionId": "mv_001",
    },
    {
        "id": "elem_asm_001",
        "name": "Assembly 1",
        "elementType": "ASSEMBLY",
        "microversionId": "mv_002",
    },
]

MOCK_PARTS = [
    {
        "partId": "part_001",
        "name": "HW-BOLT-001",
        "properties": [
            {"name": "Part Number", "propertyId": "pn_001", "value": ""},
            {"name": "Description", "propertyId": "desc_001", "value": "Hex bolt"},
            {"name": "Material", "propertyId": "mat_001", "value": "Steel"},
            {"name": "Appearance", "propertyId": "app_001", "value": "Zinc Plated"},
            {"name": "Vendor", "propertyId": "vnd_001", "value": "Fastenal"},
            {"name": "Project", "propertyId": "prj_001", "value": "Project Alpha"},
            {"name": "Revision", "propertyId": "rev_001", "value": "B"},
            {
                "name": "Custom Finish",
                "propertyId": "cf_001",
                "value": "Hot-dip galvanized",
            },
        ],
        "material": {"displayName": "Steel, Mild"},
    },
    {
        "partId": "part_002",
        "name": "90185A632",
        "properties": [
            {"name": "Part Number", "propertyId": "pn_002", "value": "90185A632"},
            {
                "name": "Description",
                "propertyId": "desc_002",
                "value": "McMaster bolt",
            },
        ],
    },
]

MOCK_MASS_PROPERTIES = {
    "bodies": {
        "body_001": {
            "mass": [0.045],
            "volume": [5.73e-6],
            "periphery": [0.00234],
        }
    }
}

MOCK_PART_METADATA = {
    "items": [
        {
            "partId": "part_001",
            "href": "https://cad.onshape.com/api/metadata/...",
            "properties": [
                {"name": "Part Number", "propertyId": "pn_001", "value": ""},
                {"name": "Description", "propertyId": "desc_001", "value": ""},
            ],
        }
    ]
}

MOCK_ASSEMBLY_BOM = {
    "bomTable": {
        "items": [
            {
                "name": "HW-BOLT-001",
                "partNumber": "HW-BOLT-001",
                "quantity": 4,
            },
            {
                "name": "HW-NUT-001",
                "partNumber": "HW-NUT-001",
                "quantity": 4,
            },
            {
                "name": "Unknown Part",
                "partNumber": "",
                "quantity": 1,
            },
        ]
    }
}


class OnshapeTestCase(TransactionComponentCase):
    """Base test case with Onshape backend and mock fixtures."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.backend = cls.env["onshape.backend"].create(
            {
                "name": "Test Onshape",
                "base_url": "https://cad.onshape.com",
                "auth_mode": "hmac",
                "api_key": "test_api_key",
                "api_secret": "test_api_secret",
                "onshape_company_id": "team_test_001",
                "state": "active",
            }
        )
        cls.product_bolt = cls.env["product.product"].create(
            {
                "name": "Hex Bolt 3/8-16",
                "default_code": "HW-BOLT-001",
                "type": "product",
            }
        )
        cls.product_nut = cls.env["product.product"].create(
            {
                "name": "Hex Nut 3/8-16",
                "default_code": "HW-NUT-001",
                "type": "product",
            }
        )
        cls.product_mcmaster = cls.env["product.product"].create(
            {
                "name": "McMaster Grade 5 Bolt",
                "default_code": "90185A632",
                "type": "product",
            }
        )
        cls.category = cls.env["product.category"].create(
            {"name": "Onshape Test Category"}
        )

    def _create_mock_document(self):
        return self.env["onshape.document"].create(
            {
                "backend_id": self.backend.id,
                "name": "Test Assembly",
                "onshape_document_id": "abc123def456abc123def456",
                "onshape_default_workspace_id": "ws_001",
                "document_type": "assembly",
            }
        )

    def _create_mock_element(self, document, elem_type="partstudio"):
        return self.env["onshape.document.element"].create(
            {
                "document_id": document.id,
                "name": f"Test {elem_type}",
                "onshape_element_id": f"elem_{elem_type}_001",
                "element_type": elem_type,
            }
        )

    def _mock_adapter(self):
        """Return a mock adapter with pre-configured responses."""
        adapter = MagicMock()
        adapter.check_credentials.return_value = (True, "OK")
        adapter.search_documents.return_value = MOCK_DOCUMENTS_RESPONSE
        adapter.read_document.return_value = MOCK_DOCUMENT
        adapter.read_document_elements.return_value = MOCK_ELEMENTS
        adapter.read_parts.return_value = MOCK_PARTS
        adapter.read_part_metadata.return_value = MOCK_PART_METADATA
        adapter.read_mass_properties.return_value = MOCK_MASS_PROPERTIES
        adapter.read_assembly_bom.return_value = MOCK_ASSEMBLY_BOM
        adapter.write_part_metadata.return_value = {}
        adapter.read_thumbnail.return_value = None
        return adapter
