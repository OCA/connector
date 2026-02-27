# Copyright 2024 Kencove Farm Fence Supplies
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging

from odoo import fields

from odoo.addons.component.core import Component

_logger = logging.getLogger(__name__)


class OnshapeProductExporter(Component):
    """Export product data (Part Number, Description) to Onshape.

    Ported from enrich_onshape_metadata.py:update_part_properties().
    Writes the Odoo default_code as Onshape "Part Number" and
    product name as Onshape "Description".
    """

    _name = "onshape.product.exporter"
    _inherit = "onshape.base"
    _usage = "record.exporter"
    _apply_on = "onshape.product.product"

    def run(self, binding):
        adapter = self.component(usage="backend.adapter")
        mapper = self.component(usage="export.mapper")

        doc = binding.onshape_document_id
        if not doc:
            _logger.warning("Binding %s has no document, skipping export", binding.id)
            return

        ws_id = doc.onshape_default_workspace_id
        elem_id = binding.onshape_element_id
        if not ws_id or not elem_id:
            _logger.warning(
                "Binding %s missing workspace/element, skipping export",
                binding.id,
            )
            return

        # Get current metadata to find property IDs
        meta = adapter.read_part_metadata(
            doc.onshape_document_id,
            ws_id,
            elem_id,
        )
        if not meta:
            _logger.warning("Could not fetch metadata for binding %s", binding.id)
            return

        export_values = mapper.map_record(binding)

        items = meta.get("items", [])
        if not items:
            _logger.info(
                "No metadata items for binding %s — skipping export", binding.id
            )
            return

        for part_item in items:
            # Optionally filter by partId
            if (
                binding.onshape_part_id
                and part_item.get("partId") != binding.onshape_part_id
            ):
                continue

            # Build update list: match export values to existing property IDs
            properties_update = []
            for prop in part_item.get("properties", []):
                prop_name = prop.get("name", "")
                if prop_name in export_values and export_values[prop_name]:
                    properties_update.append(
                        {
                            "propertyId": prop["propertyId"],
                            "value": str(export_values[prop_name]),
                        }
                    )

            if properties_update:
                adapter.write_part_metadata(
                    doc.onshape_document_id,
                    ws_id,
                    elem_id,
                    [
                        {
                            "href": part_item.get("href", ""),
                            "properties": properties_update,
                        }
                    ],
                )

        binding.write({"sync_date": fields.Datetime.now()})
        _logger.info(
            "Exported product data for binding %s (SKU: %s)",
            binding.id,
            export_values.get("Part Number", ""),
        )
