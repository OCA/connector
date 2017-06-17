# -*- coding: utf-8 -*-
# Copyright 2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import models
from ..core import EventWorkContext


class Base(models.AbstractModel):
    """ The base model, which is implicitly inherited by all models. """
    _inherit = 'base'

    def _event(self, name, model_name=None, collection=None,
               components_registry=None):
        model_name = model_name or self._name
        if collection:
            work = EventWorkContext(collection=collection,
                                    model_name=model_name,
                                    from_recordset=self,
                                    components_registry=components_registry)
        else:
            work = EventWorkContext(env=self.env, model_name=model_name,
                                    from_recordset=self,
                                    components_registry=components_registry)

        producer = work.component_by_name('base.event.producer')
        return producer.collect_events(name)
