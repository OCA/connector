# -*- coding: utf-8 -*-
# Author: Simone Orsi
# Copyright 2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).


import odoo.tests.common as common


class TestAll(common.TransactionCase):

    def setUp(self):
        super(TestAll, self).setUp()
        self.backend_model = self.env['importer.backend']

    def test_backend_create(self):
        b1 = self.backend_model.create({})
        self.assertTrue(b1)
