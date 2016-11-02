# -*- coding: utf-8 -*-
# Copyright 2012-2016 Camptocamp
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import odoo.tests.common as common

from openerp.addons.queue_job.utils import is_module_installed, get_odoo_module


class TestUtils(common.TransactionCase):

    def test_is_module_installed(self):
        """ Test on an installed module """
        self.assertTrue(is_module_installed(self.env, 'queue_job'))

    def test_is_module_uninstalled(self):
        """ Test on an installed module """
        self.assertFalse(is_module_installed(self.env, 'lambda'))

    def test_get_odoo_module(self):
        """ Odoo module is found from a Python path """
        self.assertEquals(get_odoo_module(TestUtils), 'queue_job')
