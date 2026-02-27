# Copyright 2024 Kencove Farm Fence Supplies
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from psycopg2 import IntegrityError

from .common import OnshapeTestCase


class TestDocumentImport(OnshapeTestCase):
    """Test document and element creation."""

    def test_document_creation(self):
        doc = self._create_mock_document()
        self.assertTrue(doc.exists())
        self.assertEqual(doc.onshape_document_id, "abc123def456abc123def456")
        self.assertEqual(doc.document_type, "assembly")
        self.assertIn("cad.onshape.com", doc.onshape_url)

    def test_element_creation(self):
        doc = self._create_mock_document()
        elem = self._create_mock_element(doc, "partstudio")
        self.assertTrue(elem.exists())
        self.assertEqual(elem.element_type, "partstudio")
        self.assertEqual(elem.document_id, doc)

    def test_document_display_name(self):
        doc = self._create_mock_document()
        self.assertIn("[abc123de]", doc.display_name)
        self.assertIn("Test Assembly", doc.display_name)

    def test_document_unique_constraint(self):
        self._create_mock_document()
        with self.assertRaises(IntegrityError), self.cr.savepoint():
            self._create_mock_document()


class TestProductRecordImporter(OnshapeTestCase):
    """Test the product record importer with match logic."""

    def test_no_auto_create_skips_unmatched(self):
        """When auto_create is False and no match, no binding is created."""
        self.backend.write({"auto_create_products": False})
        doc = self._create_mock_document()
        elem = self._create_mock_element(doc)

        with self.backend.work_on("onshape.product.product") as work:
            importer = work.component(usage="record.importer")
            result = importer.run(
                backend=self.backend,
                document=doc,
                element=elem,
                part_data={
                    "partId": "unknown_part",
                    "name": "TOTALLY_UNKNOWN_XYZ",
                    "properties": [],
                },
            )
        self.assertIsNone(result)

    def test_auto_create_creates_product(self):
        """When auto_create is True and no match, a product is created."""
        self.backend.write(
            {
                "auto_create_products": True,
                "default_product_category_id": self.category.id,
            }
        )
        doc = self._create_mock_document()
        elem = self._create_mock_element(doc)

        with self.backend.work_on("onshape.product.product") as work:
            importer = work.component(usage="record.importer")
            binding = importer.run(
                backend=self.backend,
                document=doc,
                element=elem,
                part_data={
                    "partId": "new_part_001",
                    "name": "Brand New Part",
                    "properties": [],
                },
            )
        self.assertTrue(binding)
        self.assertEqual(binding.match_type, "auto_created")
        self.assertEqual(binding.odoo_id.categ_id, self.category)

    def test_exact_match_binding(self):
        """Part named same as existing SKU creates binding with exact match."""
        doc = self._create_mock_document()
        elem = self._create_mock_element(doc)

        with self.backend.work_on("onshape.product.product") as work:
            importer = work.component(usage="record.importer")
            binding = importer.run(
                backend=self.backend,
                document=doc,
                element=elem,
                part_data={
                    "partId": "part_bolt",
                    "name": "HW-BOLT-001",
                    "properties": [],
                },
            )
        self.assertTrue(binding)
        self.assertEqual(binding.odoo_id, self.product_bolt)
        self.assertEqual(binding.match_type, "exact_filename")

    def test_update_existing_binding(self):
        """Re-importing same part updates existing binding."""
        doc = self._create_mock_document()
        elem = self._create_mock_element(doc)

        with self.backend.work_on("onshape.product.product") as work:
            importer = work.component(usage="record.importer")
            binding1 = importer.run(
                backend=self.backend,
                document=doc,
                element=elem,
                part_data={
                    "partId": "part_bolt",
                    "name": "HW-BOLT-001",
                    "properties": [],
                },
            )
            # Import again - should update, not create new
            binding2 = importer.run(
                backend=self.backend,
                document=doc,
                element=elem,
                part_data={
                    "partId": "part_bolt",
                    "name": "HW-BOLT-001",
                    "properties": [
                        {"name": "Material", "value": "Stainless"},
                    ],
                },
            )
        self.assertEqual(binding1, binding2)
        self.assertEqual(binding2.onshape_material, "Stainless")
