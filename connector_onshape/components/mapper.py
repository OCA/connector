# Copyright 2024 Kencove Farm Fence Supplies
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import json
import logging
import re

from odoo.addons.component.core import Component

_logger = logging.getLogger(__name__)

# McMaster-Carr catalog number pattern (e.g., 90185A632, 91845A30)
MCMASTER_RE = re.compile(r"(\d{4,}[A-Z]\d+)")
# Version suffix pattern (e.g., .0001, .0002)
VERSION_SUFFIX_RE = re.compile(r"\.\d{4}$")

# Standard Onshape metadata property names we recognize
KNOWN_PROPERTIES = {
    "Part Number",
    "Name",
    "Description",
    "Material",
    "Appearance",
    "Revision",
    "Vendor",
    "Project",
    "Weight",
    "Title 1",
    "Title 2",
    "Title 3",
}


class OnshapeProductImportMapper(Component):
    """Map Onshape part data to onshape.product.product fields.

    Extracts all available metadata from Onshape API responses including:
    - Standard properties: Part Number, Description, Material, Appearance,
      Revision, Vendor, Project
    - Mass properties: mass, volume, surface_area (from separate API call)
    - Document owner / author / designer
    - Custom properties (stored as JSON)

    Also includes the 4-strategy SKU matching ported from
    match_cad_to_odoo.py lines 60-92.
    """

    _name = "onshape.product.import.mapper"
    _inherit = "onshape.base"
    _usage = "import.mapper"
    _apply_on = "onshape.product.product"

    # Map of Onshape property name → binding field name
    PROPERTY_FIELD_MAP = {
        "Part Number": "onshape_part_number",
        "Description": "onshape_description",
        "Material": "onshape_material",
        "Appearance": "onshape_appearance",
        "Revision": "onshape_revision",
        "Vendor": "onshape_vendor",
        "Project": "onshape_project",
    }

    def map_record(self, part_data, document=None, element=None):
        vals = {
            "onshape_name": part_data.get("name", ""),
            "onshape_state": "in_progress",
        }
        # Initialize all mapped fields to empty
        for field_name in self.PROPERTY_FIELD_MAP.values():
            vals[field_name] = ""
        vals.update(
            {
                "onshape_author": "",
                "onshape_designer": "",
            }
        )

        custom_props = self._extract_properties(part_data, vals)
        self._apply_fallbacks(part_data, vals)
        self._extract_mass_properties(part_data, vals)

        if document and document.owner:
            vals["onshape_author"] = document.owner

        if custom_props:
            vals["onshape_custom_properties"] = json.dumps(
                custom_props, ensure_ascii=False
            )

        return vals

    def _extract_properties(self, part_data, vals):
        """Extract standard and custom properties from metadata."""
        custom_props = {}
        for prop in part_data.get("properties", []):
            name = prop.get("name", "")
            value = prop.get("value", "")
            if not value:
                continue
            field_name = self.PROPERTY_FIELD_MAP.get(name)
            if field_name:
                vals[field_name] = value
            elif name not in KNOWN_PROPERTIES:
                custom_props[name] = value
        return custom_props

    def _apply_fallbacks(self, part_data, vals):
        """Apply fallback values from part data for material and appearance."""
        if not vals["onshape_material"]:
            mat = part_data.get("material", {})
            if isinstance(mat, dict):
                vals["onshape_material"] = mat.get("displayName", "")
        if not vals["onshape_appearance"]:
            appearance = part_data.get("appearance", {})
            if isinstance(appearance, dict):
                vals["onshape_appearance"] = appearance.get("name", "")

    @staticmethod
    def _extract_mass_properties(part_data, vals):
        """Extract mass, volume, surface area from injected mass properties."""
        bodies = part_data.get("mass_properties", {}).get("bodies", {})
        if not bodies:
            return
        total_mass = 0.0
        total_volume = 0.0
        total_area = 0.0
        for body_data in bodies.values():
            total_mass += (body_data.get("mass") or [0.0])[0]
            total_volume += (body_data.get("volume") or [0.0])[0]
            total_area += (body_data.get("periphery") or [0.0])[0]
        if total_mass:
            vals["onshape_mass"] = total_mass
        if total_volume:
            vals["onshape_volume"] = total_volume
        if total_area:
            vals["onshape_surface_area"] = total_area

    def _search_by_code(self, code):
        """Search for a product by exact default_code."""
        if not code:
            return self.env["product.product"]
        return self.env["product.product"].search(
            [("default_code", "=", code)], limit=1
        )

    def match_product(self, part_data):
        """Try to match an Onshape part to an existing Odoo product.

        4-strategy matching ported from match_cad_to_odoo.py:
        1. Exact part name match against default_code
        2. Part number from metadata against default_code
        3. McMaster catalog number extraction
        4. Case-insensitive match

        Returns (product.product recordset, match_type) or (None, None).
        """
        part_name = part_data.get("name", "").strip()
        part_number = ""

        for prop in part_data.get("properties", []):
            if prop.get("name") == "Part Number":
                part_number = (prop.get("value") or "").strip()
                break

        # Clean name: strip CAD extensions and version suffixes
        base_name = re.sub(r"\.(ipt|iam|dwg|idw)$", "", part_name, flags=re.IGNORECASE)
        base_no_ver = VERSION_SUFFIX_RE.sub("", base_name)

        result = self._match_by_name(base_no_ver, base_name)
        if not result[0]:
            result = self._match_by_part_number(part_number)
        if not result[0]:
            result = self._match_by_mcmaster(base_no_ver)
        if not result[0]:
            result = self._match_case_insensitive(base_no_ver)
        return result

    def _match_by_name(self, base_no_ver, base_name):
        """Strategy 1: Exact filename match against default_code."""
        if not base_no_ver:
            return None, None
        product = self._search_by_code(base_no_ver)
        if product:
            return product, "exact_filename"
        product = self._search_by_code(base_name)
        if product:
            return product, "exact_filename_versioned"
        return None, None

    def _match_by_part_number(self, part_number):
        """Strategy 2: Part number from Onshape metadata."""
        if not part_number:
            return None, None
        product = self._search_by_code(part_number)
        if product:
            return product, "part_name"
        pn_prefix = part_number.split("_")[0].strip()
        if pn_prefix and pn_prefix != part_number:
            product = self._search_by_code(pn_prefix)
            if product:
                return product, "part_name_prefix"
        return None, None

    def _match_by_mcmaster(self, base_no_ver):
        """Strategy 3: McMaster catalog number extraction."""
        if not base_no_ver:
            return None, None
        mcmaster_match = MCMASTER_RE.search(base_no_ver)
        if mcmaster_match:
            product = self._search_by_code(mcmaster_match.group(1))
            if product:
                return product, "mcmaster_catalog"
        return None, None

    def _match_case_insensitive(self, base_no_ver):
        """Strategy 4: Case-insensitive match via casing variants."""
        if not base_no_ver:
            return None, None
        for variant in (base_no_ver.upper(), base_no_ver.lower()):
            if variant == base_no_ver:
                continue  # Already tried exact in strategy 1
            product = self._search_by_code(variant)
            if product:
                return product, "case_insensitive"
        return None, None


class OnshapeProductExportMapper(Component):
    """Map Odoo product data to Onshape metadata fields.

    Exports Odoo product fields to Onshape standard metadata properties.
    """

    _name = "onshape.product.export.mapper"
    _inherit = "onshape.base"
    _usage = "export.mapper"
    _apply_on = "onshape.product.product"

    def map_record(self, binding):
        vals = {
            "Part Number": binding.odoo_id.default_code or "",
            "Description": binding.odoo_id.name or "",
        }
        # Include weight from Odoo if set (export back to Onshape)
        if binding.odoo_id.weight:
            vals["Weight"] = str(binding.odoo_id.weight)
        return vals
