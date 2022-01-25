# Copyright 2013-2017 Camptocamp SA
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html)

from odoo.addons.component.tests.common import TransactionComponentCase


class TestDefaultBinder(TransactionComponentCase):
    """Test the default binder implementation using Components"""

    def setUp(self):
        super().setUp()

        # create our backend, in case of components,
        # the version would not be required
        self.backend_record = self.env["test.backend"].create({})

    def test_default_binder(self):
        """Small scenario with the default binder"""
        # create a work context with the model we want to work with
        with self.backend_record.work_on("connector.test.binding") as work:
            # get our binder component (for the model in whe work context)
            self.binder = work.component(usage="binder")
            test_record = self.env["connector.test.record"].create({})
            test_binding = self.env["connector.test.binding"].create(
                {"backend_id": self.backend_record.id, "odoo_id": test_record.id}
            )

            # bind the test binding to external id = 99
            self.binder.bind(99, test_binding)
            # find the odoo binding bound to external record 99
            binding = self.binder.to_internal(99)
            self.assertEqual(binding, test_binding)
            # find the odoo record bound to external record 99
            record = self.binder.to_internal(99, unwrap=True)
            self.assertEqual(record, test_record)
            # find the external record bound to odoo binding
            external_id = self.binder.to_external(test_binding)
            self.assertEqual(external_id, 99)
            # find the external record bound to odoo record
            external_id = self.binder.to_external(test_record, wrap=True)
            self.assertEqual(external_id, 99)
            self.assertEqual(self.binder.unwrap_model(), "connector.test.record")
            # unwrapping the binding should give the same binding
            self.assertEqual(self.binder.unwrap_binding(test_binding), test_record)
