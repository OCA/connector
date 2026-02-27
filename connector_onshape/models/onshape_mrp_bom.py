# Copyright 2024 Kencove Farm Fence Supplies
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class OnshapeMrpBom(models.Model):
    _name = "onshape.mrp.bom"
    _description = "Onshape BOM Binding"
    _inherits = {"mrp.bom": "odoo_id"}

    odoo_id = fields.Many2one(
        "mrp.bom",
        string="Odoo BOM",
        required=True,
        ondelete="cascade",
        index=True,
    )
    backend_id = fields.Many2one(
        "onshape.backend",
        string="Backend",
        required=True,
        ondelete="restrict",
        index=True,
    )
    external_id = fields.Char(
        string="External ID",
        index=True,
        help="Compound key: document_id/element_id",
    )
    onshape_document_id = fields.Many2one(
        "onshape.document",
        string="Onshape Document",
        ondelete="set null",
        index=True,
    )
    onshape_element_id = fields.Char(string="Element ID")
    match_score = fields.Float(
        string="Component Match Score",
        digits=(5, 3),
        help="Percentage of components matched between Onshape and Odoo.",
    )
    last_bom_hash = fields.Char(
        string="BOM Hash",
        help="Hash of BOM contents for change detection.",
    )
    sync_date = fields.Datetime(string="Last Sync Date")
    onshape_url = fields.Char(
        string="Onshape URL",
        compute="_compute_onshape_url",
        store=True,
    )

    _sql_constraints = [
        (
            "unique_binding",
            "unique(backend_id, external_id)",
            "This Onshape assembly BOM is already bound on this backend.",
        ),
    ]

    @api.depends(
        "onshape_document_id.backend_id.base_url",
        "onshape_document_id.onshape_document_id",
        "onshape_document_id.onshape_default_workspace_id",
        "onshape_element_id",
    )
    def _compute_onshape_url(self):
        for rec in self:
            doc = rec.onshape_document_id
            base = doc.backend_id.base_url if doc else False
            did = doc.onshape_document_id if doc else False
            workspace = doc.onshape_default_workspace_id if doc else False
            elem = rec.onshape_element_id
            if base and did and workspace and elem:
                rec.onshape_url = f"{base}/documents/{did}/w/{workspace}/e/{elem}"
            else:
                rec.onshape_url = False
