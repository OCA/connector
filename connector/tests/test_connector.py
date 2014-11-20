# -*- coding: utf-8 -*-

import unittest2

from openerp.addons.connector.connector import ConnectorUnit


class test_connector_unit(unittest2.TestCase):
    """ Test Connector Unit """

    def test_connector_unit_model_name(self):
        model = 'res.users'

        class ModelUnit(ConnectorUnit):
            _model_name = model

        self.assertEqual(ModelUnit.model_name, [model])

    def test_connector_unit_no_model_name(self):
        with self.assertRaises(NotImplementedError):
            ConnectorUnit.model_name  # pylint: disable=W0104
