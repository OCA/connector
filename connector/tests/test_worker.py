# -*- coding: utf-8 -*-

import unittest2

from openerp.addons.connector.queue.queue import JobsQueue


class test_worker(unittest2.TestCase):
    """ Test Worker """

    def setUp(self):
        self.queue = JobsQueue()
