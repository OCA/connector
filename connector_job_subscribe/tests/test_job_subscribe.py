# -*- coding: utf-8 -*-
# Copyright 2016 Cédric Pigeon
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import openerp.tests.common as common

from openerp.addons.connector.session import ConnectorSession
from openerp.addons.connector.queue.job import (
    Job,
    OpenERPJobStorage,
)


def task_a(session, model_name):
    """ Task description
    """


class TestJobSubscribe(common.TransactionCase):

    def setUp(self):
        super(TestJobSubscribe, self).setUp()
        grp_connector_manager = self.ref("connector.group_connector_manager")
        self.other_partner_a = self.env['res.partner'].create(
            {"name": "My Company a",
             "is_company": True,
             "email": "test@tes.ttest",
             })
        self.other_user_a = self.env['res.users'].create(
            {"partner_id": self.other_partner_a.id,
             "login": "my_login a",
             "name": "my user",
             "groups_id": [(4, grp_connector_manager)]
             })
        self.other_partner_b = self.env['res.partner'].create(
            {"name": "My Company b",
             "is_company": True,
             "email": "test@tes.ttest",
             })
        self.other_user_b = self.env['res.users'].create(
            {"partner_id": self.other_partner_b.id,
             "login": "my_login_b",
             "name": "my user 1",
             "groups_id": [(4, grp_connector_manager)]
             })

        self.session = ConnectorSession.from_env(self.env)

    def _create_job(self):
        test_job = Job(func=task_a)
        storage = OpenERPJobStorage(self.session)
        storage.store(test_job)
        stored = storage.db_record_from_uuid(test_job.uuid)
        self.assertEqual(len(stored), 1)
        return stored

    def test_job_subscription(self):
        """
            When a job is created, all user of group
            connector.group_connector_manager are automatically set as
            follower except if the flag subscribe_job is not set
        """

        #################################
        # Test 1: All users are followers
        #################################
        stored = self._create_job()
        stored._subscribe_users()
        users = self.env['res.users'].search(
            [('groups_id', '=', self.ref('connector.group_connector_manager'))]
        )
        self.assertEqual(len(stored.message_follower_ids), len(users))
        expected_partners = [u.partner_id for u in users]
        self.assertSetEqual(set(stored.message_follower_ids),
                            set(expected_partners))
        followers_id = [f.id for f in stored.message_follower_ids]
        self.assertIn(self.other_partner_a.id, followers_id)
        self.assertIn(self.other_partner_b.id, followers_id)

        ###########################################
        # Test 2: User b request to not be follower
        ###########################################
        self.other_user_b.write({'subscribe_job': False})
        stored = self._create_job()
        stored._subscribe_users()
        users = self.env['res.users'].search(
            [('groups_id', '=', self.ref('connector.group_connector_manager')),
             ('subscribe_job', '=', True)]
        )
        self.assertEqual(len(stored.message_follower_ids), len(users))
        expected_partners = [u.partner_id for u in users]
        self.assertSetEqual(set(stored.message_follower_ids),
                            set(expected_partners))
        followers_id = [f.id for f in stored.message_follower_ids]
        self.assertIn(self.other_partner_a.id, followers_id)
        self.assertNotIn(self.other_partner_b.id, followers_id)
