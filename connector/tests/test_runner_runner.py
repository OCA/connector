# -*- coding: utf-8 -*-
import doctest
from odoo.addons.connector.jobrunner import runner


def load_tests(loader, tests, ignore):
    tests.addTests(doctest.DocTestSuite(runner))
    return tests
