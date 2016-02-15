# -*- coding: utf-8 -*-

import unittest

from openerp.addons.connector.queue.queue import JobsQueue


class test_worker(unittest.TestCase):
    """ Test Worker """

    def setUp(self):
        self.queue = JobsQueue()
