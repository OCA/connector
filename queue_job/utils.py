# -*- coding: utf-8 -*-
# Copyright 2012-2016 Camptocamp
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)


# this is duplicated from odoo.models.MetaModel._get_addon_name() which we
# unfortunately can't use because it's an instance method and should have been
# a @staticmethod
def _get_addon_name(full_name):
    # The (OpenERP) module name can be in the ``odoo.addons`` namespace
    # or not. For instance, module ``sale`` can be imported as
    # ``odoo.addons.sale`` (the right way) or ``sale`` (for backward
    # compatibility).
    module_parts = full_name.split('.')
    if len(module_parts) > 2 and module_parts[:2] == ['odoo', 'addons']:
        addon_name = full_name.split('.')[2]
    else:
        addon_name = full_name.split('.')[0]
    return addon_name


def is_module_installed(env, module_name):
    """ Check if an Odoo addon is installed.

    :param module_name: name of the addon
    """
    # the registry maintains a set of fully loaded modules so we can
    # lookup for our module there
    return module_name in env.registry._init_modules


def get_odoo_module(cls_or_func):
    """ For a top level function or class, returns the
    name of the Odoo module where it lives.

    So we will be able to filter them according to the modules
    installation state.
    """
    # _get_addon_name is an instance method in MetaModel but it should
    # be a @staticmethod... so we pass `None` as the instance
    return _get_addon_name(cls_or_func.__module__)
