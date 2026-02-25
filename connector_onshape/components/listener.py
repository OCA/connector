# Copyright 2024 Kencove Farm Fence Supplies
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging

from odoo.addons.component.core import Component
from odoo.addons.component_event import skip_if

_logger = logging.getLogger(__name__)


class OnshapeProductListener(Component):
    """Listen for product changes and queue export to Onshape.

    When default_code or name changes on a product that is bound
    to Onshape, automatically queue an export job.

    Uses ``skip_if`` with ``connector_no_export`` context flag
    to prevent infinite loops during import operations.
    """

    _name = "onshape.product.listener"
    _inherit = "base.event.listener"
    _apply_on = ["product.product"]

    @skip_if(lambda self, record, **kwargs: self.env.context.get("connector_no_export"))
    def on_record_write(self, record, fields=None):
        if not fields:
            return
        export_fields = {"default_code", "name"}
        if not export_fields.intersection(set(fields)):
            return

        for binding in record.onshape_bind_ids:
            if binding.backend_id.state != "active":
                continue
            binding.with_delay(
                priority=15,
                description=(
                    f"Export product {record.default_code or record.name} "
                    f"to Onshape"
                ),
            ).export_record()
