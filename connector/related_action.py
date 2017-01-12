# -*- coding: utf-8 -*-
# Copyright 2014-2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

"""
Related Actions

Related actions are associated with jobs.
When called on a job, they will return an action to the client.

"""

from odoo import _
from .connector import ConnectorEnvironment, Binder


def unwrap_binding(env, job, id_pos=2, binder_class=Binder):
    """ Open a form view with the unwrapped record.

    For instance, for a job on a ``magento.product.product``,
    it will open a ``product.product`` form view with the unwrapped
    record.

    :param id_pos: position of the binding ID in the args
    :param binder_class: base class to search for the binder
    """
    binding_model = job.args[0]
    # shift one to the left because env is not in job.args
    binding_id = job.args[id_pos - 1]
    action = {
        'name': _('Related Record'),
        'type': 'ir.actions.act_window',
        'view_type': 'form',
        'view_mode': 'form',
    }
    # try to get an unwrapped record
    binding = env[binding_model].browse(binding_id)
    if not binding.exists():
        # it has been deleted
        return None
    env = ConnectorEnvironment(binding.backend_id, env, binding_model)
    binder = env.get_connector_unit(binder_class)
    try:
        model = binder.unwrap_model()
        record_id = binder.unwrap_binding(binding_id)
    except ValueError:
        # the binding record will be displayed
        action.update({
            'res_model': binding_model,
            'res_id': binding_id,
        })
    else:
        # the unwrapped record will be displayed
        action.update({
            'res_model': model,
            'res_id': record_id,
        })
    return action
