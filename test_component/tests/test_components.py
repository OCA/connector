# Copyright 2019 Camptocamp SA
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html)

from odoo.addons.component.tests.common import TransactionComponentCase


class TestComponentInheritance(TransactionComponentCase):
    def setUp(self):
        super().setUp()
        self.collection = self.env["test.component.collection"].create({"name": "Test"})

    def test_inherit_base(self):
        with self.collection.work_on("res.users") as work:
            component = work.component_by_name("base")
            self.assertEqual("test_inherit_base", component.test_inherit_base())

    def test_inherit_component(self):
        with self.collection.work_on("res.users") as work:
            component = work.component_by_name("mapper")
            self.assertEqual(
                "test_inherit_component", component.test_inherit_component()
            )

    def test_inherit_prototype_component(self):
        with self.collection.work_on("res.users") as work:
            component = work.component_by_name("test.mapper")
            self.assertEqual(
                "test_inherit_component", component.test_inherit_component()
            )
            self.assertEqual("test.mapper", component.name())
