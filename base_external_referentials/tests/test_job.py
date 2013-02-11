# -*- coding: utf-8 -*-

import mock
import unittest2
from datetime import datetime, timedelta

from openerp.addons.base_external_referentials.queue.job import Job


def task_b(session):
    pass


def task_a(session):
    pass


def dummy_task(session):
    return 'ok'


def dummy_task_args(session, a, b, c=None):
    return a + b + c


class test_job(unittest2.TestCase):
    """ Test Job """

    def setUp(self):
        self.session = mock.MagicMock()

    def test_new_job(self):
        """
        Create a job
        """
        job = Job(func=task_a)
        self.assertEqual(job.func, task_a)

    def test_priority(self):
        """ The lower the priority number, the higher
        the priority is"""
        job_a = Job(func=task_a, priority=10)
        job_b = Job(func=task_b, priority=5)
        self.assertGreater(job_a, job_b)

    def test_only_after(self):
        """ When an `only_after` datetime is defined, it should
        be executed after a job without one.
        """
        date = datetime.now() + timedelta(hours=3)
        job_a = Job(func=task_a, priority=10, only_after=date)
        job_b = Job(func=task_b, priority=10)
        self.assertGreater(job_a, job_b)

    def test_perform(self):
        job = Job(func=dummy_task)
        result = job.perform(self.session)
        self.assertEqual(result, 'ok')

    def test_perform_args(self):
        job = Job(func=dummy_task_args,
                  args=('o', 'k'),
                  kwargs={'c': '!'})
        result = job.perform(self.session)
        self.assertEqual(result, 'ok!')
