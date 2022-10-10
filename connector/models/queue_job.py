# -*- coding: utf-8 -*-
# Copyright 2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import _, api, models
from ..connector import ConnectorEnvironment, Binder


class QueueJob(models.Model):

    _inherit = 'queue.job'

    @api.multi
    def related_action_unwrap_binding(self, binder_class=Binder,
                                      component_usage='binder'):
        """ Open a form view with the unwrapped record.

        For instance, for a job on a ``magento.product.product``,
        it will open a ``product.product`` form view with the unwrapped
        record.

        :param binder_class: base class to search for the binder (for old API)
        :param component_usage: base component usage to search for the binder
        """
        self.ensure_one()
        model_name = self.model_name
        binding = self.env[model_name].browse(self.record_ids).exists()
        if not binding:
            return None
        if len(binding) > 1:
            # not handled
            return None
        action = {
            'name': _('Related Record'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
        }
        if binding.backend_id._backend_type:  # old connector API
            # try to get unwrapped records
            env = ConnectorEnvironment(
                binding.backend_id, binding._name
            )
            binder = env.get_connector_unit(binder_class)
        else:  # new component API
            with binding.backend_id.work_on(binding._name) as work:
                binder = work.component(usage=component_usage)
        try:
            model = binder.unwrap_model()
            record = binder.unwrap_binding(binding)
            # the unwrapped record will be displayed
            action.update({
                'res_model': model,
                'res_id': record.id,
            })
        except ValueError:
            # the binding record will be displayed
            action.update({
                'res_model': binding._name,
                'res_id': binding.id,
            })
        return action
