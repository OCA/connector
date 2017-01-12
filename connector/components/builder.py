# -*- coding: utf-8 -*-
# Copyright 2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import odoo
from odoo import api, models
from .core import MetaComponent


class ComponentGlobalRegistry(dict):
    """ Store all the components by name

    Allow to _inherit components.

    Another registry allow to register components
    on a particular backend and to find them back.

    """

components = ComponentGlobalRegistry()


class ComponentBuilder(models.AbstractModel):
    _name = 'connector.component.builder'
    _description = 'Connector Component Builder'

    @api.model_cr
    def _register_hook(self):
        graph = odoo.modules.graph.Graph()
        graph.add_module(self.env.cr, 'base')

        self.env.cr.execute(
            "SELECT name "
            "FROM ir_module_module "
            "WHERE state IN ('installed', 'to upgrade', 'to update')"
        )
        module_list = [name for (name,) in self.env.cr.fetchall()
                       if name not in graph]
        graph.add_modules(self.env.cr, module_list)

        for module in graph:
            self.load_components(module.name, components)

    def load_components(self, module, registry):
        for component_class in MetaComponent.components[module]:
            component_class._build_component(registry)
