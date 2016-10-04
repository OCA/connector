# -*- coding: utf-8 -*-
import doctest
from odoo.addons.queue_job.jobrunner import channels


def load_tests(loader, tests, ignore):
    tests.addTests(doctest.DocTestSuite(channels))
    return tests
