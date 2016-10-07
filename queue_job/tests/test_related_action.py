# -*- coding: utf-8 -*-

import unittest

import odoo.tests.common as common
from odoo.addons.queue_job.job import Job, related_action
from .common import start_jobify, stop_jobify, related_actionify


def task_no_related(env):
    pass


def task_related_none(env):
    pass


def task_related_return(env):
    pass


def open_url(env, job, url=None):
    subject = job.args[0]
    return {
        'type': 'ir.actions.act_url',
        'target': 'new',
        'url': url.format(subject=subject),
    }


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
        self.assertIsNone(job.related_action(self.env))

    def test_return_none(self):
        """ Job with related action returning None """
        # default action returns None
        with related_actionify(self.method):
            job = Job(self.method)
            self.assertIsNone(job.related_action(self.env))

    def test_return(self):
        """ Job with related action check if action returns correctly """
        def action(env, job):
            return env, job
        with related_actionify(self.method, action=action):
            job = Job(self.method)
            act_env, act_job = job.related_action(self.env)
            self.assertEqual(act_env, self.env)
            self.assertEqual(act_job, job)

    def test_kwargs(self):
        """ Job with related action check if action propagates kwargs """
        def action(env, job, a=1, b=2):
            return a, b
        with related_actionify(self.method, action=action, b=4):
            job = Job(self.method)
            self.assertEqual(job.related_action(self.env), (1, 4))

    def test_store_related_action(self):
        """ Call the related action on the model """
        with related_actionify(self.method,
                               action=open_url,
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
