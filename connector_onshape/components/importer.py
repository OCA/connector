# Copyright 2024 Kencove Farm Fence Supplies
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import hashlib
import json
import logging
from datetime import datetime

from odoo import fields

from odoo.addons.component.core import Component

_logger = logging.getLogger(__name__)


def _parse_iso_datetime(value):
    """Convert ISO 8601 datetime string to Odoo-compatible naive format.

    Handles the ``Z`` suffix that ``datetime.fromisoformat`` only supports
    from Python 3.11+.
    """
    if not value:
        return False
    try:
        # Replace Z suffix for Python < 3.11 compatibility
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError):
        return False


class OnshapeDocumentBatchImporter(Component):
    """Batch importer for Onshape documents.

    Lists all documents from Onshape and queues
    individual record imports via queue_job.
    """

    _name = "onshape.document.batch.importer"
    _inherit = "onshape.base"
    _usage = "batch.importer"
    _apply_on = "onshape.document"

    def run(self, backend, **kwargs):
        adapter = self.component(usage="backend.adapter")
        offset = 0
        limit = 20
        total_queued = 0

        while True:
            result = adapter.search_documents(
                owner_id=backend.onshape_company_id,
                offset=offset,
                limit=limit,
            )
            items = result.get("items", [])
            if not items:
                break

            for doc_data in items:
                doc_id = doc_data.get("id")
                if not doc_id:
                    continue
                existing = self.env["onshape.document"].search(
                    [
                        ("backend_id", "=", backend.id),
                        ("onshape_document_id", "=", doc_id),
                    ],
                    limit=1,
                )
                if existing:
                    # Update name/timestamps
                    vals = {"name": doc_data.get("name", existing.name)}
                    modified = _parse_iso_datetime(doc_data.get("modifiedAt"))
                    if modified:
                        vals["modified_at"] = modified
                    existing.write(vals)
                else:
                    self._import_document(backend, doc_data)
                total_queued += 1

            if len(items) < limit:
                break
            offset += limit

        _logger.info(
            "Onshape document batch import: processed %d documents",
            total_queued,
        )

    def _import_document(self, backend, doc_data):
        """Create an onshape.document and import its elements."""
        default_ws = doc_data.get("defaultWorkspace") or {}
        workspace_id = (
            default_ws.get("id")
            or default_ws.get("workspaceId")
            or doc_data.get("defaultWorkspaceId", "")
        )
        owner_data = doc_data.get("owner") or {}

        vals = {
            "backend_id": backend.id,
            "name": doc_data.get("name", "Untitled"),
            "onshape_document_id": doc_data["id"],
            "onshape_default_workspace_id": workspace_id,
            "owner": owner_data.get("name", ""),
            "created_at": _parse_iso_datetime(doc_data.get("createdAt")),
            "modified_at": _parse_iso_datetime(doc_data.get("modifiedAt")),
        }
        document = self.env["onshape.document"].create(vals)

        # Import elements
        if workspace_id:
            self._import_elements(backend, document, workspace_id)

        # Auto-register webhook for per-document mode (Free/EDU plans)
        if (
            not backend.onshape_company_id
            and backend.state == "active"
            and backend.webhook_secret
        ):
            backend._register_document_webhook(document)

        return document

    def _import_elements(self, backend, document, workspace_id):
        adapter = self.component(usage="backend.adapter")
        try:
            elements = adapter.read_document_elements(
                document.onshape_document_id,
                workspace_id,
            )
        except Exception:
            _logger.warning(
                "Could not fetch elements for document %s",
                document.onshape_document_id,
            )
            return

        if not isinstance(elements, list):
            return

        type_map = {
            "PARTSTUDIO": "partstudio",
            "ASSEMBLY": "assembly",
            "DRAWING": "drawing",
            "BLOB": "blob",
            "APPLICATION": "application",
        }

        has_assembly = False
        has_partstudio = False

        for elem in elements:
            elem_type_raw = elem.get("elementType", "").upper()
            elem_type = type_map.get(elem_type_raw)
            if elem_type == "assembly":
                has_assembly = True
            elif elem_type == "partstudio":
                has_partstudio = True

            self.env["onshape.document.element"].create(
                {
                    "document_id": document.id,
                    "name": elem.get("name", ""),
                    "onshape_element_id": elem.get("id", ""),
                    "element_type": elem_type,
                    "microversion_id": elem.get("microversionId", ""),
                }
            )

        # Infer document type
        if has_assembly:
            document.document_type = "assembly"
        elif has_partstudio:
            document.document_type = "part"


class OnshapeProductBatchImporter(Component):
    """Batch importer for Onshape product bindings.

    Iterates over all documents with part studio elements and
    imports parts as product bindings.
    """

    _name = "onshape.product.batch.importer"
    _inherit = "onshape.base"
    _usage = "batch.importer"
    _apply_on = "onshape.product.product"

    def run(self, backend, documents=None, **kwargs):
        if documents is None:
            documents = self.env["onshape.document"].search(
                [("backend_id", "=", backend.id)]
            )
        adapter = self.component(usage="backend.adapter")
        total = 0

        for doc in documents:
            ws_id = doc.onshape_default_workspace_id
            if not ws_id:
                continue

            part_studio_elements = doc.element_ids.filtered(
                lambda e: e.element_type == "partstudio"
            )
            for elem in part_studio_elements:
                try:
                    parts_data = adapter.read_parts(
                        doc.onshape_document_id,
                        ws_id,
                        elem.onshape_element_id,
                    )
                except Exception:
                    _logger.warning(
                        "Could not fetch parts for %s/%s",
                        doc.onshape_document_id,
                        elem.onshape_element_id,
                    )
                    continue

                if not isinstance(parts_data, list):
                    continue

                for part in parts_data:
                    part_id = part.get("partId", "")
                    if not part_id:
                        continue

                    record_importer = self.component(
                        usage="record.importer",
                        model_name="onshape.product.product",
                    )
                    record_importer.run(
                        backend=backend,
                        document=doc,
                        element=elem,
                        part_data=part,
                    )
                    total += 1

        _logger.info("Onshape product batch import: processed %d parts", total)


class OnshapeProductRecordImporter(Component):
    """Record importer for a single Onshape part → product binding."""

    _name = "onshape.product.record.importer"
    _inherit = "onshape.base"
    _usage = "record.importer"
    _apply_on = "onshape.product.product"

    def run(self, backend, document, element, part_data):
        binder = self.component(usage="binder")
        mapper = self.component(usage="import.mapper")
        adapter = self.component(usage="backend.adapter")

        part_id = part_data.get("partId", "")
        external_id = binder.make_compound_id(
            document.onshape_document_id,
            element.onshape_element_id,
            part_id,
        )

        # Enrich part_data with mass properties if available
        self._enrich_mass_properties(adapter, document, element, part_id, part_data)

        existing = binder.to_internal(external_id)
        if existing:
            # Update existing binding
            vals = mapper.map_record(
                part_data,
                document=document,
                element=element,
            )
            update_vals = {
                k: v
                for k, v in vals.items()
                if k
                not in (
                    "odoo_id",
                    "backend_id",
                    "external_id",
                    "match_type",
                    "onshape_state",
                )
            }
            update_vals["sync_date"] = fields.Datetime.now()
            existing.with_context(connector_no_export=True).write(update_vals)
            return existing

        # New binding
        vals = mapper.map_record(
            part_data,
            document=document,
            element=element,
        )
        vals.update(
            {
                "backend_id": backend.id,
                "external_id": external_id,
                "onshape_document_id": document.id,
                "onshape_element_id": element.onshape_element_id,
                "onshape_part_id": part_id,
                "sync_date": fields.Datetime.now(),
            }
        )

        # Find or create Odoo product
        odoo_product = vals.pop("odoo_id", None)
        if not odoo_product:
            odoo_product = self._match_or_create_product(backend, part_data, vals)
        if not odoo_product:
            _logger.debug(
                "No match and auto_create disabled, skipping part %s",
                part_data.get("name", ""),
            )
            return None
        vals["odoo_id"] = odoo_product.id

        binding = self.env["onshape.product.product"].create(vals)
        return binding

    def _enrich_mass_properties(self, adapter, document, element, part_id, part_data):
        """Fetch mass properties from Onshape and inject into part_data."""
        try:
            mass_data = adapter.read_mass_properties(
                document.onshape_document_id,
                document.onshape_default_workspace_id,
                element.onshape_element_id,
                part_id=part_id,
            )
            if mass_data and isinstance(mass_data, dict):
                part_data["mass_properties"] = mass_data
        except Exception:
            _logger.debug(
                "Could not fetch mass properties for %s/%s",
                document.onshape_document_id,
                part_id,
            )

    def _match_or_create_product(self, backend, part_data, vals):
        """Try to match to an existing product, or create a new one."""
        mapper = self.component(usage="import.mapper")
        product, match_type = mapper.match_product(part_data)

        if product:
            vals["match_type"] = match_type
            return product

        if not backend.auto_create_products:
            return None

        # Auto-create product
        part_name = part_data.get("name", "Unknown Part")
        create_vals = {
            "name": part_name,
            "type": "product",
        }
        categ = backend.default_product_category_id
        if categ:
            create_vals["categ_id"] = categ.id
        product = self.env["product.product"].create(create_vals)
        vals["match_type"] = "auto_created"
        return product


class OnshapeBomBatchImporter(Component):
    """Batch importer for Onshape assembly BOMs."""

    _name = "onshape.bom.batch.importer"
    _inherit = "onshape.base"
    _usage = "batch.importer"
    _apply_on = "onshape.mrp.bom"

    def run(self, backend, **kwargs):
        documents = self.env["onshape.document"].search(
            [
                ("backend_id", "=", backend.id),
                ("document_type", "=", "assembly"),
            ]
        )
        total = 0

        for doc in documents:
            ws_id = doc.onshape_default_workspace_id
            if not ws_id:
                continue

            assembly_elements = doc.element_ids.filtered(
                lambda e: e.element_type == "assembly"
            )
            for elem in assembly_elements:
                record_importer = self.component(
                    usage="record.importer",
                    model_name="onshape.mrp.bom",
                )
                record_importer.run(
                    backend=backend,
                    document=doc,
                    element=elem,
                )
                total += 1

        _logger.info("Onshape BOM batch import: processed %d assemblies", total)


class OnshapeBomRecordImporter(Component):
    """Record importer for a single Onshape assembly → mrp.bom binding."""

    _name = "onshape.bom.record.importer"
    _inherit = "onshape.base"
    _usage = "record.importer"
    _apply_on = "onshape.mrp.bom"

    def run(self, backend, document, element):
        adapter = self.component(usage="backend.adapter")
        binder = self.component(usage="binder")

        external_id = binder.make_compound_id(
            document.onshape_document_id,
            element.onshape_element_id,
        )

        # Fetch BOM from Onshape
        try:
            bom_data = adapter.read_assembly_bom(
                document.onshape_document_id,
                document.onshape_default_workspace_id,
                element.onshape_element_id,
            )
        except Exception:
            _logger.warning(
                "Could not fetch BOM for %s/%s",
                document.onshape_document_id,
                element.onshape_element_id,
            )
            return

        bom_items = bom_data.get("bomTable", {}).get("items", [])
        if not bom_items:
            return

        # Compute BOM hash for change detection
        bom_hash = hashlib.md5(
            json.dumps(bom_items, sort_keys=True).encode()
        ).hexdigest()

        existing = binder.to_internal(external_id)
        if existing and existing.last_bom_hash == bom_hash:
            _logger.debug("BOM %s unchanged, skipping", external_id)
            return existing

        # Find or create the parent product binding
        parent_binding = self._find_parent_product(backend, document)
        if not parent_binding:
            _logger.warning(
                "No parent product for assembly %s, skipping BOM",
                document.name,
            )
            return

        # Build BOM lines
        bom_lines = self._build_bom_lines(backend, bom_items)

        if existing:
            # Update existing BOM
            existing.odoo_id.bom_line_ids.unlink()
            existing.odoo_id.write({"bom_line_ids": bom_lines})
            existing.write(
                {
                    "last_bom_hash": bom_hash,
                    "sync_date": fields.Datetime.now(),
                    "match_score": self._compute_match_score(bom_items, bom_lines),
                }
            )
            return existing

        # Create new BOM + binding
        bom_vals = {
            "product_tmpl_id": parent_binding.odoo_id.product_tmpl_id.id,
            "product_id": parent_binding.odoo_id.id,
            "type": "normal",
            "bom_line_ids": bom_lines,
        }
        bom = self.env["mrp.bom"].create(bom_vals)

        binding = self.env["onshape.mrp.bom"].create(
            {
                "odoo_id": bom.id,
                "backend_id": backend.id,
                "external_id": external_id,
                "onshape_document_id": document.id,
                "onshape_element_id": element.onshape_element_id,
                "last_bom_hash": bom_hash,
                "sync_date": fields.Datetime.now(),
                "match_score": self._compute_match_score(bom_items, bom_lines),
            }
        )
        return binding

    def _find_parent_product(self, backend, document):
        bindings = self.env["onshape.product.product"].search(
            [
                ("backend_id", "=", backend.id),
                ("onshape_document_id", "=", document.id),
            ],
            limit=1,
        )
        return bindings

    def _build_bom_lines(self, backend, bom_items):
        lines = []
        for item in bom_items:
            item_qty = item.get("quantity", 1)

            # Try to find a matching product binding by part name
            product = self._find_component_product(backend, item)
            if not product:
                continue

            lines.append(
                (
                    0,
                    0,
                    {
                        "product_id": product.id,
                        "product_qty": item_qty,
                    },
                )
            )
        return lines

    def _find_component_product(self, backend, bom_item):
        """Find an Odoo product matching a BOM component item."""
        item_name = bom_item.get("name", "")
        part_number = bom_item.get("partNumber", "")

        # Try by part number (SKU)
        if part_number:
            product = self.env["product.product"].search(
                [("default_code", "=", part_number)], limit=1
            )
            if product:
                return product

        # Try by name
        if item_name:
            product = self.env["product.product"].search(
                [("name", "=", item_name)], limit=1
            )
            if product:
                return product

        # Try binding lookup
        if part_number:
            binding = self.env["onshape.product.product"].search(
                [
                    ("backend_id", "=", backend.id),
                    ("onshape_part_number", "=", part_number),
                ],
                limit=1,
            )
            if binding:
                return binding.odoo_id

        return None

    def _compute_match_score(self, bom_items, bom_lines):
        total = len(bom_items)
        if total == 0:
            return 0.0
        matched = len(bom_lines)
        return round(matched / total * 100, 1)
