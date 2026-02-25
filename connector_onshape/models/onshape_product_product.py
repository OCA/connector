# Copyright 2024 Kencove Farm Fence Supplies
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class OnshapeProductProduct(models.Model):
    _name = "onshape.product.product"
    _description = "Onshape Product Binding"
    _inherits = {"product.product": "odoo_id"}

    odoo_id = fields.Many2one(
        "product.product",
        string="Odoo Product",
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
        help="Compound key: document_id/element_id/part_id",
    )
    onshape_document_id = fields.Many2one(
        "onshape.document",
        string="Onshape Document",
        ondelete="set null",
        index=True,
    )
    onshape_element_id = fields.Char(string="Element ID")
    onshape_part_id = fields.Char(string="Part ID")
    onshape_part_number = fields.Char(
        help="Part number as stored in Onshape metadata.",
    )
    onshape_name = fields.Char(
        string="Onshape Part Name",
        help="Part name as stored in Onshape.",
    )
    onshape_description = fields.Char(
        help="Description property from Onshape metadata.",
    )
    onshape_material = fields.Char()
    onshape_appearance = fields.Char(
        string="Appearance",
        help="Appearance / color / finish from Onshape.",
    )
    onshape_revision = fields.Char(
        string="Revision",
        help="Revision identifier from Onshape release management.",
    )
    onshape_mass = fields.Float(
        string="Mass (kg)",
        digits=(16, 6),
        help="Computed mass from Onshape mass properties (kg).",
    )
    onshape_volume = fields.Float(
        string="Volume (m³)",
        digits=(16, 9),
        help="Computed volume from Onshape mass properties (m³).",
    )
    onshape_surface_area = fields.Float(
        string="Surface Area (m²)",
        digits=(16, 6),
        help="Computed surface area from Onshape mass properties (m²).",
    )
    onshape_author = fields.Char(
        string="Author",
        help="Original author from Inventor metadata or Onshape document owner.",
    )
    onshape_designer = fields.Char(
        string="Designer",
        help="Last designer/editor from Inventor Design Tracking metadata.",
    )
    onshape_vendor = fields.Char(
        string="Vendor",
        help="Vendor property from Onshape metadata.",
    )
    onshape_project = fields.Char(
        string="Project",
        help="Project property from Onshape metadata.",
    )
    onshape_custom_properties = fields.Text(
        string="Custom Properties (JSON)",
        help="Additional Onshape custom properties stored as JSON.",
    )
    onshape_state = fields.Selection(
        [
            ("in_progress", "In Progress"),
            ("pending", "Pending"),
            ("released", "Released"),
            ("obsolete", "Obsolete"),
        ],
        string="Onshape Lifecycle State",
        default="in_progress",
    )
    onshape_thumbnail = fields.Binary(attachment=True)
    match_type = fields.Selection(
        [
            ("exact_filename", "Exact Filename"),
            ("exact_filename_versioned", "Exact Filename (Versioned)"),
            ("part_name", "Part Name"),
            ("part_name_prefix", "Part Name Prefix"),
            ("mcmaster_catalog", "McMaster Catalog"),
            ("case_insensitive", "Case Insensitive"),
            ("manual", "Manual"),
            ("auto_created", "Auto Created"),
        ],
        help="How this Onshape part was matched to the Odoo product.",
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
            "This Onshape part is already bound on this backend.",
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
            if (
                doc
                and doc.backend_id.base_url
                and doc.onshape_document_id
                and doc.onshape_default_workspace_id
                and rec.onshape_element_id
            ):
                rec.onshape_url = (
                    f"{doc.backend_id.base_url}"
                    f"/documents/{doc.onshape_document_id}"
                    f"/w/{doc.onshape_default_workspace_id}"
                    f"/e/{rec.onshape_element_id}"
                )
            else:
                rec.onshape_url = False

    def export_record(self):
        self.ensure_one()
        with self.backend_id.work_on("onshape.product.product") as work:
            exporter = work.component(usage="record.exporter")
            return exporter.run(self)
