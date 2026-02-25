# Copyright 2024 Kencove Farm Fence Supplies
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.addons.component.core import Component


class OnshapeBinder(Component):
    """Binder for Onshape bindings.

    Handles compound external IDs (e.g. doc_id/elem_id/part_id).
    """

    _name = "onshape.binder"
    _inherit = ["onshape.base", "base.binder"]
    _usage = "binder"
    _external_field = "external_id"
    _apply_on = [
        "onshape.product.product",
        "onshape.mrp.bom",
    ]

    def to_internal(self, external_id, unwrap=False):
        bindings = self.model.search(
            [
                ("external_id", "=", external_id),
                ("backend_id", "=", self.backend_record.id),
            ],
            limit=1,
        )
        if not bindings:
            return self.model.browse()
        if unwrap:
            return bindings.odoo_id
        return bindings

    def to_external(self, binding, wrap=False):
        if wrap:
            binding = self.model.search(
                [
                    ("odoo_id", "=", binding.id),
                    ("backend_id", "=", self.backend_record.id),
                ],
                limit=1,
            )
            if not binding:
                return None
        return binding.external_id

    def bind(self, external_id, binding):
        binding.write({"external_id": external_id})

    @staticmethod
    def make_compound_id(document_id, element_id, part_id=None):
        if part_id:
            return f"{document_id}/{element_id}/{part_id}"
        return f"{document_id}/{element_id}"

    @staticmethod
    def split_compound_id(external_id):
        if not external_id:
            raise ValueError("external_id must be a non-empty string")
        parts = external_id.split("/")
        if len(parts) == 3:
            return {
                "document_id": parts[0],
                "element_id": parts[1],
                "part_id": parts[2],
            }
        if len(parts) == 2:
            return {"document_id": parts[0], "element_id": parts[1]}
        raise ValueError("Cannot parse compound ID: %r" % external_id)
