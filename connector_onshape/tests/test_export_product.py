# Copyright 2024 Kencove Farm Fence Supplies
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from .common import OnshapeTestCase


class TestProductExportMapper(OnshapeTestCase):
    """Test the export mapper."""

    def test_export_mapper_values(self):
        doc = self._create_mock_document()
        binding = self.env["onshape.product.product"].create(
            {
                "odoo_id": self.product_bolt.id,
                "backend_id": self.backend.id,
                "external_id": "abc123/elem_001/part_001",
                "onshape_document_id": doc.id,
                "onshape_element_id": "elem_001",
                "onshape_part_id": "part_001",
            }
        )
        with self.backend.work_on("onshape.product.product") as work:
            mapper = work.component(usage="export.mapper")
            vals = mapper.map_record(binding)

        self.assertEqual(vals["Part Number"], "HW-BOLT-001")
        self.assertEqual(vals["Description"], "Hex Bolt 3/8-16")

    def test_export_mapper_empty_sku(self):
        product_no_sku = self.env["product.product"].create(
            {
                "name": "No SKU Product",
                "type": "product",
            }
        )
        doc = self._create_mock_document()
        binding = self.env["onshape.product.product"].create(
            {
                "odoo_id": product_no_sku.id,
                "backend_id": self.backend.id,
                "external_id": "abc123/elem_001/part_099",
                "onshape_document_id": doc.id,
            }
        )
        with self.backend.work_on("onshape.product.product") as work:
            mapper = work.component(usage="export.mapper")
            vals = mapper.map_record(binding)

        self.assertEqual(vals["Part Number"], "")
        self.assertEqual(vals["Description"], "No SKU Product")


class TestBinder(OnshapeTestCase):
    """Test the compound ID binder."""

    def test_make_compound_id_with_part(self):
        from ..components.binder import OnshapeBinder

        result = OnshapeBinder.make_compound_id("doc1", "elem1", "part1")
        self.assertEqual(result, "doc1/elem1/part1")

    def test_make_compound_id_without_part(self):
        from ..components.binder import OnshapeBinder

        result = OnshapeBinder.make_compound_id("doc1", "elem1")
        self.assertEqual(result, "doc1/elem1")

    def test_split_compound_id(self):
        from ..components.binder import OnshapeBinder

        result = OnshapeBinder.split_compound_id("doc1/elem1/part1")
        self.assertEqual(
            result,
            {"document_id": "doc1", "element_id": "elem1", "part_id": "part1"},
        )

        result = OnshapeBinder.split_compound_id("doc1/elem1")
        self.assertEqual(result, {"document_id": "doc1", "element_id": "elem1"})

    def test_split_compound_id_malformed(self):
        from ..components.binder import OnshapeBinder

        with self.assertRaises(ValueError):
            OnshapeBinder.split_compound_id("doc1")

        with self.assertRaises(ValueError):
            OnshapeBinder.split_compound_id("")

        with self.assertRaises(ValueError):
            OnshapeBinder.split_compound_id(None)
