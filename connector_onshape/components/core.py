# Copyright 2024 Kencove Farm Fence Supplies
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.addons.component.core import AbstractComponent


class OnshapeBaseComponent(AbstractComponent):
    """Base component for Onshape connector.

    All Onshape components inherit from this to share the common
    _collection name.
    """

    _name = "onshape.base"
    _inherit = "base.connector"
    _collection = "onshape.backend"
