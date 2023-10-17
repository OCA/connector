# Copyright 2018 Camptocamp SA
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import mock

from odoo import api
from odoo.modules.registry import Registry
from odoo.tests import common

from odoo.addons.component.core import WorkContext
from odoo.addons.component.tests.common import TransactionComponentRegistryCase
from odoo.addons.queue_job.exception import RetryableJobError


class TestLocker(TransactionComponentRegistryCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(
            context=dict(
                cls.env.context,
                mail_create_nolog=True,
                mail_create_nosubscribe=True,
                mail_notrack=True,
                no_reset_password=True,
                tracking_disable=True,
            )
        )
        cls.backend = mock.MagicMock(name="backend")
        cls.backend.env = cls.env

        cls.registry2 = Registry(common.get_db_name())
        cls.cr2 = cls.registry2.cursor()
        cls.env2 = api.Environment(cls.cr2, cls.env.uid, {})
        cls.backend2 = mock.MagicMock(name="backend2")
        cls.backend2.env = cls.env2

        @cls.addClassCleanup
        def reset_cr2():
            # rollback and close the cursor, and reset the environments
            cls.env2.reset()
            cls.cr2.rollback()
            cls.cr2.close()

    def test_lock(self):
        """Lock a record"""
        main_partner = self.env.ref("base.main_partner")
        work = WorkContext(model_name="res.partner", collection=self.backend)
        work.component("record.locker").lock(main_partner)

        main_partner2 = self.env2.ref("base.main_partner")
        work2 = WorkContext(model_name="res.partner", collection=self.backend2)
        locker2 = work2.component("record.locker")
        with self.assertRaises(RetryableJobError):
            locker2.lock(main_partner2)
