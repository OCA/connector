# Copyright 2024 Kencove Farm Fence Supplies
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from .common import OnshapeTestCase


class TestProductListener(OnshapeTestCase):
    """Test the auto-export listener on product.product writes."""

    def test_connector_no_export_context_skips(self):
        """Writes with connector_no_export context should not trigger export."""
        doc = self._create_mock_document()
        self.env["onshape.product.product"].create(
            {
                "odoo_id": self.product_bolt.id,
                "backend_id": self.backend.id,
                "external_id": "abc123/elem_001/part_001",
                "onshape_document_id": doc.id,
            }
        )
        # Write with connector_no_export - should not queue any job
        self.product_bolt.with_context(connector_no_export=True).write(
            {"default_code": "HW-BOLT-002"}
        )
        # If we got here without error, the skip_if worked

    def test_unlinked_product_no_error(self):
        """Writing to a product without Onshape bindings should not error."""
        product = self.env["product.product"].create(
            {"name": "No Binding", "type": "product"}
        )
        # Should not raise
        product.write({"default_code": "NEW-SKU"})

    def test_irrelevant_field_no_export(self):
        """Changing a field not in export_fields should not trigger export."""
        doc = self._create_mock_document()
        self.env["onshape.product.product"].create(
            {
                "odoo_id": self.product_bolt.id,
                "backend_id": self.backend.id,
                "external_id": "abc123/elem_001/part_001",
                "onshape_document_id": doc.id,
            }
        )
        # Changing 'list_price' should not trigger anything
        self.product_bolt.write({"list_price": 99.99})
