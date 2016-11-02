# -*- coding: utf-8 -*-

import odoo.tests.common as common
from odoo.addons.queue_job.job import Job
from .common import start_jobify, stop_jobify, related_actionify


class TestRelatedAction(common.TransactionCase):
    """ Test Related Actions """

    def setUp(self):
        super(TestRelatedAction, self).setUp()
        self.method = self.env['queue.job'].testing_method
        start_jobify(self.method)

    def tearDown(self):
        super(TestRelatedAction, self).tearDown()
        stop_jobify(self.method)

    def test_no_related_action(self):
        """ Job without related action """
        job = Job(self.method)
        self.assertIsNone(job.related_action())

    def test_return_none(self):
        """ Job with related action returning None """
        # default action returns None
        with related_actionify(self.method):
            job = Job(self.method)
            self.assertIsNone(job.related_action())

    def test_return(self):
        """ Job with related action check if action returns correctly """
        with related_actionify(self.method, action='testing_related_method'):
            job = Job(self.method)
            act_job, act_kwargs = job.related_action()
            self.assertEqual(act_job, job.db_record())
            self.assertEqual(act_kwargs, {})

    def test_kwargs(self):
        """ Job with related action check if action propagates kwargs """
        action = 'testing_related_method'
        with related_actionify(self.method, action=action, b=4):
            job = Job(self.method)
            self.assertEqual(job.related_action(), (job.db_record(), {'b': 4}))

    def test_store_related_action(self):
        """ Call the related action on the model """
        action = 'testing_related_method'
        with related_actionify(self.method,
                               action=action,
                               url='https://en.wikipedia.org/wiki/{subject}'):
            job = Job(self.method, args=('Discworld',))
            job.store()
            stored_job = self.env['queue.job'].search(
                [('uuid', '=', job.uuid)]
            )
            self.assertEqual(len(stored_job), 1)
            expected = {'type': 'ir.actions.act_url',
                        'target': 'new',
                        'url': 'https://en.wikipedia.org/wiki/Discworld',
                        }
            self.assertEquals(stored_job.open_related_action(), expected)
