# Copyright 2024 Kencove Farm Fence Supplies
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from .common import OnshapeTestCase


class TestBomBinding(OnshapeTestCase):
    """Test BOM binding creation and match scoring."""

    def test_create_bom_binding(self):
        doc = self._create_mock_document()
        bom = self.env["mrp.bom"].create(
            {
                "product_tmpl_id": self.product_bolt.product_tmpl_id.id,
                "product_id": self.product_bolt.id,
                "type": "normal",
                "bom_line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product_nut.id,
                            "product_qty": 4,
                        },
                    )
                ],
            }
        )
        binding = self.env["onshape.mrp.bom"].create(
            {
                "odoo_id": bom.id,
                "backend_id": self.backend.id,
                "external_id": "abc123/elem_asm_001",
                "onshape_document_id": doc.id,
                "onshape_element_id": "elem_asm_001",
                "match_score": 0.667,
                "last_bom_hash": "abc123hash",
            }
        )
        self.assertTrue(binding.exists())
        self.assertTrue(bom.onshape_linked)
        self.assertEqual(binding.match_score, 0.667)

    def test_bom_hash_change_detection(self):
        doc = self._create_mock_document()
        bom = self.env["mrp.bom"].create(
            {
                "product_tmpl_id": self.product_bolt.product_tmpl_id.id,
                "type": "normal",
            }
        )
        binding = self.env["onshape.mrp.bom"].create(
            {
                "odoo_id": bom.id,
                "backend_id": self.backend.id,
                "external_id": "abc123/elem_asm_001",
                "onshape_document_id": doc.id,
                "last_bom_hash": "old_hash",
            }
        )
        self.assertEqual(binding.last_bom_hash, "old_hash")
        binding.write({"last_bom_hash": "new_hash"})
        self.assertEqual(binding.last_bom_hash, "new_hash")
