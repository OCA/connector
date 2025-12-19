# Copyright 2026 Kencove
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html)

from odoo.addons.component.core import Component


class AmazonBinder(Component):
    _name = "amazon.binder"
    _inherit = "base.binder"
    _usage = "binder"
    _backend_model_name = "amazon.backend"

    # TODO: extend with helper methods for multi-marketplace keys if needed
