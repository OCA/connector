# Copyright 2024 Kencove Farm Fence Supplies
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class OnshapeDocument(models.Model):
    _name = "onshape.document"
    _description = "Onshape Document"
    _order = "name"

    backend_id = fields.Many2one(
        "onshape.backend",
        string="Backend",
        required=True,
        ondelete="cascade",
        index=True,
    )
    name = fields.Char(required=True, index=True)
    onshape_document_id = fields.Char(
        string="Document ID",
        required=True,
        index=True,
        help="24-character hex Onshape document identifier.",
    )
    onshape_default_workspace_id = fields.Char(
        string="Default Workspace ID",
        help="Active workspace for this document.",
    )
    document_type = fields.Selection(
        [
            ("assembly", "Assembly"),
            ("part", "Part Studio"),
            ("drawing", "Drawing"),
            ("other", "Other"),
        ],
        default="other",
    )
    thumbnail = fields.Binary(attachment=True)
    element_ids = fields.One2many(
        "onshape.document.element", "document_id", string="Elements"
    )
    product_binding_ids = fields.One2many(
        "onshape.product.product",
        "onshape_document_id",
        string="Product Bindings",
    )
    bom_binding_ids = fields.One2many(
        "onshape.mrp.bom",
        "onshape_document_id",
        string="BOM Bindings",
    )
    onshape_url = fields.Char(
        string="Onshape URL",
        compute="_compute_onshape_url",
        store=True,
    )
    onshape_webhook_id = fields.Char(
        string="Webhook ID",
        index=True,
        help="Onshape webhook ID registered for this document. "
        "Empty means no active webhook.",
    )
    owner = fields.Char()
    created_at = fields.Datetime(string="Created in Onshape")
    modified_at = fields.Datetime(string="Last Modified in Onshape")

    _sql_constraints = [
        (
            "unique_document",
            "unique(backend_id, onshape_document_id)",
            "This Onshape document is already registered on this backend.",
        ),
    ]

    @api.depends("backend_id.base_url", "onshape_document_id")
    def _compute_onshape_url(self):
        for rec in self:
            if rec.backend_id.base_url and rec.onshape_document_id:
                rec.onshape_url = (
                    f"{rec.backend_id.base_url}" f"/documents/{rec.onshape_document_id}"
                )
            else:
                rec.onshape_url = False

    def name_get(self):
        result = []
        for rec in self:
            if rec.onshape_document_id:
                name = f"[{rec.onshape_document_id[:8]}] {rec.name}"
            else:
                name = rec.name or ""
            result.append((rec.id, name))
        return result


class OnshapeDocumentElement(models.Model):
    _name = "onshape.document.element"
    _description = "Onshape Document Element"

    document_id = fields.Many2one(
        "onshape.document",
        string="Document",
        required=True,
        ondelete="cascade",
        index=True,
    )
    backend_id = fields.Many2one(related="document_id.backend_id", store=True)
    name = fields.Char(required=True)
    onshape_element_id = fields.Char(string="Element ID", required=True, index=True)
    element_type = fields.Selection(
        [
            ("partstudio", "Part Studio"),
            ("assembly", "Assembly"),
            ("drawing", "Drawing"),
            ("blob", "Blob"),
            ("application", "Application"),
        ],
    )
    microversion_id = fields.Char(string="Microversion ID")

    _sql_constraints = [
        (
            "unique_element",
            "unique(document_id, onshape_element_id)",
            "This element already exists in this document.",
        ),
    ]
