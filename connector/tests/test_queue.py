# -*- coding: utf-8 -*-

import unittest2
from datetime import timedelta

from openerp.addons.connector.queue.queue import JobsQueue
from openerp.addons.connector.queue.job import Job


def dummy_task(session):
    pass


class test_queue(unittest2.TestCase):
    """ Test Queue """

    def setUp(self):
        self.queue = JobsQueue()

    def test_sort(self):
        """ Sort: the lowest priority number has the highest priority.
        A job with a `eta` datetime is less priority in any case.
        """
        job1 = Job(dummy_task, priority=10)
        job2 = Job(dummy_task, priority=5)
        job3 = Job(dummy_task, priority=15,
                   eta=timedelta(hours=2))
        job4 = Job(dummy_task, priority=15,
                   eta=timedelta(hours=1))
        job5 = Job(dummy_task, priority=1,
                   eta=timedelta(hours=2))
        self.queue.enqueue(job1)
        self.queue.enqueue(job2)
        self.queue.enqueue(job3)
        self.queue.enqueue(job4)
        self.queue.enqueue(job5)
        self.assertEqual(self.queue.dequeue(), job2)
        self.assertEqual(self.queue.dequeue(), job1)
        self.assertEqual(self.queue.dequeue(), job4)
        self.assertEqual(self.queue.dequeue(), job3)
        self.assertEqual(self.queue.dequeue(), job5)
