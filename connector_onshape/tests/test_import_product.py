# Copyright 2024 Kencove Farm Fence Supplies
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from psycopg2 import IntegrityError

from .common import MOCK_PARTS, OnshapeTestCase


class TestProductImportMapper(OnshapeTestCase):
    """Test the 4-strategy SKU matching logic."""

    def _get_mapper(self):
        with self.backend.work_on("onshape.product.product") as work:
            return work.component(usage="import.mapper")

    def test_exact_filename_match(self):
        mapper = self._get_mapper()
        part_data = {"name": "HW-BOLT-001", "properties": []}
        product, match_type = mapper.match_product(part_data)
        self.assertEqual(product, self.product_bolt)
        self.assertEqual(match_type, "exact_filename")

    def test_exact_filename_with_extension(self):
        mapper = self._get_mapper()
        part_data = {"name": "HW-BOLT-001.ipt", "properties": []}
        product, match_type = mapper.match_product(part_data)
        self.assertEqual(product, self.product_bolt)
        self.assertEqual(match_type, "exact_filename")

    def test_exact_filename_with_version(self):
        mapper = self._get_mapper()
        part_data = {"name": "HW-BOLT-001.0001", "properties": []}
        product, match_type = mapper.match_product(part_data)
        self.assertEqual(product, self.product_bolt)
        self.assertEqual(match_type, "exact_filename")

    def test_part_number_match(self):
        mapper = self._get_mapper()
        part_data = {
            "name": "Some random name",
            "properties": [
                {"name": "Part Number", "value": "HW-NUT-001"},
            ],
        }
        product, match_type = mapper.match_product(part_data)
        self.assertEqual(product, self.product_nut)
        self.assertEqual(match_type, "part_name")

    def test_mcmaster_catalog_match(self):
        mapper = self._get_mapper()
        part_data = {
            "name": "90185A632_Grade 5 Steel Bolt",
            "properties": [],
        }
        product, match_type = mapper.match_product(part_data)
        self.assertEqual(product, self.product_mcmaster)
        self.assertEqual(match_type, "mcmaster_catalog")

    def test_case_insensitive_match(self):
        mapper = self._get_mapper()
        part_data = {"name": "hw-bolt-001", "properties": []}
        product, match_type = mapper.match_product(part_data)
        self.assertEqual(product, self.product_bolt)
        self.assertEqual(match_type, "case_insensitive")

    def test_no_match(self):
        mapper = self._get_mapper()
        part_data = {"name": "TOTALLY_UNKNOWN_PART", "properties": []}
        product, match_type = mapper.match_product(part_data)
        self.assertIsNone(product)
        self.assertIsNone(match_type)

    def test_map_record_extracts_fields(self):
        mapper = self._get_mapper()
        vals = mapper.map_record(MOCK_PARTS[0])
        self.assertEqual(vals["onshape_name"], "HW-BOLT-001")
        self.assertEqual(vals["onshape_material"], "Steel")
        self.assertEqual(vals["onshape_description"], "Hex bolt")
        self.assertEqual(vals["onshape_appearance"], "Zinc Plated")
        self.assertEqual(vals["onshape_vendor"], "Fastenal")
        self.assertEqual(vals["onshape_project"], "Project Alpha")
        self.assertEqual(vals["onshape_revision"], "B")

    def test_map_record_custom_properties(self):
        """Custom/unknown properties are stored as JSON."""
        import json

        mapper = self._get_mapper()
        vals = mapper.map_record(MOCK_PARTS[0])
        custom = json.loads(vals.get("onshape_custom_properties", "{}"))
        self.assertEqual(custom.get("Custom Finish"), "Hot-dip galvanized")

    def test_map_record_mass_properties(self):
        """Mass properties injected by importer are mapped."""
        from ..tests.common import MOCK_MASS_PROPERTIES

        mapper = self._get_mapper()
        part_data = dict(MOCK_PARTS[0])
        part_data["mass_properties"] = MOCK_MASS_PROPERTIES
        vals = mapper.map_record(part_data)
        self.assertAlmostEqual(vals["onshape_mass"], 0.045, places=4)
        self.assertAlmostEqual(vals["onshape_volume"], 5.73e-6, places=10)
        self.assertAlmostEqual(vals["onshape_surface_area"], 0.00234, places=6)

    def test_map_record_material_fallback(self):
        """Material falls back to part data displayName if not in properties."""
        mapper = self._get_mapper()
        part_data = {
            "name": "Test Part",
            "properties": [],
            "material": {"displayName": "Aluminum 6061"},
        }
        vals = mapper.map_record(part_data)
        self.assertEqual(vals["onshape_material"], "Aluminum 6061")

    def test_map_record_with_part_number(self):
        mapper = self._get_mapper()
        vals = mapper.map_record(MOCK_PARTS[1])
        self.assertEqual(vals["onshape_part_number"], "90185A632")


class TestProductBinding(OnshapeTestCase):
    """Test product binding creation."""

    def test_create_binding(self):
        doc = self._create_mock_document()
        self._create_mock_element(doc)
        binding = self.env["onshape.product.product"].create(
            {
                "odoo_id": self.product_bolt.id,
                "backend_id": self.backend.id,
                "external_id": "abc123/elem_ps_001/part_001",
                "onshape_document_id": doc.id,
                "onshape_element_id": "elem_ps_001",
                "onshape_part_id": "part_001",
                "onshape_name": "HW-BOLT-001",
                "match_type": "exact_filename",
            }
        )
        self.assertTrue(binding.exists())
        self.assertTrue(self.product_bolt.onshape_linked)
        self.assertIn("cad.onshape.com", binding.onshape_url or "")

    def test_compound_id_unique_constraint(self):
        doc = self._create_mock_document()
        self.env["onshape.product.product"].create(
            {
                "odoo_id": self.product_bolt.id,
                "backend_id": self.backend.id,
                "external_id": "abc123/elem_001/part_001",
                "onshape_document_id": doc.id,
            }
        )
        with self.assertRaises(IntegrityError), self.cr.savepoint():
            self.env["onshape.product.product"].create(
                {
                    "odoo_id": self.product_nut.id,
                    "backend_id": self.backend.id,
                    "external_id": "abc123/elem_001/part_001",
                    "onshape_document_id": doc.id,
                }
            )
