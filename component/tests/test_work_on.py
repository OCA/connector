# -*- coding: utf-8 -*-
# Copyright 2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import mock
from odoo.tests import common
from odoo.addons.component.core import (
    WorkContext,
)


class TestWorkOn(common.TransactionCase):

    def setUp(self):
        super(TestWorkOn, self).setUp()
        self.collection = self.env['collection.base']

    def test_collection_work_on(self):
        collection_record = self.collection.new()
        work = collection_record.work_on('res.partner')
        self.assertEquals(collection_record, work.collection)
        self.assertEquals('collection.base', work.collection._name)
        self.assertEquals('res.partner', work.model_name)
        self.assertEquals(self.env['res.partner'], work.model)
        self.assertEquals(self.env, work.env)

    def test_propagate_work_on(self):
        registry = mock.Mock(name='components_registry')
        work = WorkContext(
            self.collection,
            'res.partner',
            components_registry=registry,
            test_keyword='value',
        )
        self.assertEquals(registry, work.components_registry)
        self.assertEquals('value', work.test_keyword)

        work2 = work.work_on('res.users')
        self.assertEquals(self.env, work2.env)
        self.assertEquals(self.collection, work2.collection)
        self.assertEquals('res.users', work2.model_name)
        self.assertEquals(registry, work2.components_registry)
        self.assertEquals('value', work2.test_keyword)
