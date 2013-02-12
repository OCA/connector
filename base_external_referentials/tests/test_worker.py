# -*- coding: utf-8 -*-

import unittest2
from datetime import timedelta

from openerp.addons.base_external_referentials.queue.queue import (
        JobsQueue)
from openerp.addons.base_external_referentials.queue.worker import (
        Worker)
from openerp.addons.base_external_referentials.queue.job import Job


def dummy_task(session):
    pass


class test_worker(unittest2.TestCase):
    """ Test Worker """

    def setUp(self):
        self.queue = JobsQueue()

