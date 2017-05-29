# -*- coding: utf-8 -*-
# Copyright 2016-2017 Cédric Pigeon
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tests.common import SavepointCase


class TestJobSubscribe(SavepointCase):
    """
        When a job is created, all user of group
        connector.group_connector_manager are automatically set as
        follower except if the flag subscribe_job is not set
    """

    @classmethod
    def setUpClass(cls):
        super(TestJobSubscribe, cls).setUpClass()

        # MODELS
        cls.queue_job = cls.env['queue.job']
        cls.user = cls.env['res.users']
        cls.company = cls.env['res.company']
        cls.partner = cls.env['res.partner']

        # INSTANCES
        grp_queue_job_manager = cls.env.ref(
            "queue_job.group_queue_job_manager")
        cls.other_partner_a = cls.partner.create(
            {"name": "My Company a",
             "is_company": True,
             "email": "test@tes.ttest",
             })
        cls.other_company_a = cls.company.create(
            {"name": "My Company a",
             "partner_id": cls.other_partner_a.id,
             "rml_header1": "My Company Tagline",
             "currency_id": cls.env.ref("base.EUR").id
             })
        cls.other_user_a = cls.user.create(
            {"partner_id": cls.other_partner_a.id,
             "company_id": cls.other_company_a.id,
             "company_ids": [(4, cls.other_company_a.id)],
             "login": "my_login a",
             "name": "my user",
             "groups_id": [(4, grp_queue_job_manager.id)]
             })
        cls.other_partner_b = cls.partner.create(
            {"name": "My Company b",
             "is_company": True,
             "email": "test@tes.ttest",
             })
        cls.other_company_b = cls.company.create(
            {"name": "My Company b",
             "partner_id": cls.other_partner_b.id,
             "rml_header1": "My Company Tagline",
             "currency_id": cls.env.ref("base.EUR").id
             })
        cls.other_user_b = cls.user.create(
            {"partner_id": cls.other_partner_b.id,
             "company_id": cls.other_company_b.id,
             "company_ids": [(4, cls.other_company_b.id)],
             "login": "my_login_b",
             "name": "my user 1",
             "groups_id": [(4, grp_queue_job_manager.id)]
             })

    def _subscribe_users(self, stored):
        domain = stored._subscribe_users_domain()
        users = self.user.search(domain)
        stored.message_subscribe_users(user_ids=users.ids)

    def _create_job(self, env):
        self.cr.execute('delete from queue_job')
        env['test.queue.job'].with_delay().testing_method()
        stored = self.queue_job.search([])
        self.assertEqual(len(stored), 1)
        return stored

    def test_job_subscription_subscribe_job_checked(self):
        #################################
        # Test 1: All users are followers
        #################################
        no_company_context = dict(self.env.context, company_id=None)
        no_company_env = self.env(context=no_company_context)
        stored = self._create_job(no_company_env)
        self._subscribe_users(stored)
        users = self.user.search(
            [('groups_id', '=', self.ref('queue_job.group_queue_job_manager')),
             ('subscribe_job', '=', True)]
        )
        self.assertEqual(len(stored.message_follower_ids), len(users))
        expected_partners = [u.partner_id for u in users]
        self.assertSetEqual(
            set(stored.message_follower_ids.mapped('partner_id')),
            set(expected_partners))
        followers_id = stored.message_follower_ids.mapped('partner_id.id')
        self.assertIn(self.other_partner_a.id, followers_id)
        self.assertIn(self.other_partner_b.id, followers_id)

    def test_job_subscription_subscribe_job_unchecked(self):
        ###########################################
        # Test 2: User b request to not be follower
        ###########################################
        self.other_user_b.write({'subscribe_job': False})
        no_company_context = dict(self.env.context, company_id=None)
        no_company_env = self.env(context=no_company_context)
        stored = self._create_job(no_company_env)
        self._subscribe_users(stored)
        users = self.user.search(
            [('groups_id', '=', self.ref('connector.group_connector_manager')),
             ('subscribe_job', '=', True)]
        )
        self.assertEqual(len(stored.message_follower_ids), len(users))
        expected_partners = [u.partner_id for u in users]
        self.assertSetEqual(set(stored.mapped(
            'message_follower_ids.partner_id')),
            set(expected_partners))
        followers_id = [f.id for f in stored.mapped(
            'message_follower_ids.partner_id')]
        self.assertIn(self.other_partner_a.id, followers_id)
        self.assertNotIn(self.other_partner_b.id, followers_id)
