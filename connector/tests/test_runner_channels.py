# -*- coding: utf-8 -*-
import doctest
from odoo.addons.connector.jobrunner import channels


def load_tests(loader, tests, ignore):
    tests.addTests(doctest.DocTestSuite(channels))
    return tests
