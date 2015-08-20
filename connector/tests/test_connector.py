# -*- coding: utf-8 -*-

import mock
import unittest2

from openerp.tests import common
from openerp.addons.connector import connector
from openerp.addons.connector.connector import (ConnectorUnit,
                                                ConnectorEnvironment)
from openerp.addons.connector.session import ConnectorSession


class ConnectorHelpers(unittest2.TestCase):

    def test_openerp_module_name(self):
        name = connector._get_openerp_module_name('openerp.addons.sale')
        self.assertEqual(name, 'sale')
        name = connector._get_openerp_module_name('sale')
        self.assertEqual(name, 'sale')


class TestConnectorUnit(unittest2.TestCase):
    """ Test Connector Unit """

    def test_connector_unit_for_model_names(self):
        model = 'res.users'

        class ModelUnit(ConnectorUnit):
            _model_name = model

        self.assertEqual(ModelUnit.for_model_names, [model])

    def test_connector_unit_for_model_names_several(self):
        models = ['res.users', 'res.partner']

        class ModelUnit(ConnectorUnit):
            _model_name = models

        self.assertEqual(ModelUnit.for_model_names, models)

    def test_connector_unit_no_model_name(self):
        with self.assertRaises(NotImplementedError):
            ConnectorUnit.for_model_names  # pylint: disable=W0104

    def test_match(self):

        class ModelUnit(ConnectorUnit):
            _model_name = 'res.users'

        session = mock.Mock(name='Session')

        self.assertTrue(ModelUnit.match(session, 'res.users'))
        self.assertFalse(ModelUnit.match(session, 'res.partner'))

    def test_unit_for(self):

        class ModelUnit(ConnectorUnit):
            _model_name = 'res.users'

        class ModelBinder(ConnectorUnit):
            _model_name = 'res.users'

        session = mock.MagicMock(name='Session')
        backend_record = mock.Mock(name='BackendRecord')
        backend = mock.Mock(name='Backend')
        backend_record.get_backend.return_value = backend
        # backend.get_class() is tested in test_backend.py
        backend.get_class.return_value = ModelUnit
        connector_env = connector.ConnectorEnvironment(backend_record,
                                                       session,
                                                       'res.users')
        unit = ConnectorUnit(connector_env)
        # returns an instance of ModelUnit with the same connector_env
        new_unit = unit.unit_for(ModelUnit)
        self.assertEqual(type(new_unit), ModelUnit)
        self.assertEqual(new_unit.connector_env, connector_env)

        backend.get_class.return_value = ModelBinder
        # returns an instance of ModelBinder with the same connector_env
        new_unit = unit.binder_for()
        self.assertEqual(type(new_unit), ModelBinder)
        self.assertEqual(new_unit.connector_env, connector_env)

    def test_unit_for_other_model(self):

        class ModelUnit(ConnectorUnit):
            _model_name = 'res.partner'

        class ModelBinder(ConnectorUnit):
            _model_name = 'res.partner'

        session = mock.MagicMock(name='Session')
        backend_record = mock.Mock(name='BackendRecord')
        backend = mock.Mock(name='Backend')
        backend_record.get_backend.return_value = backend
        # backend.get_class() is tested in test_backend.py
        backend.get_class.return_value = ModelUnit
        connector_env = connector.ConnectorEnvironment(backend_record,
                                                       session,
                                                       'res.users')
        unit = ConnectorUnit(connector_env)
        # returns an instance of ModelUnit with a new connector_env
        # for the different model
        new_unit = unit.unit_for(ModelUnit, model='res.partner')
        self.assertEqual(type(new_unit), ModelUnit)
        self.assertNotEqual(new_unit.connector_env, connector_env)
        self.assertEqual(new_unit.connector_env.model_name, 'res.partner')

        backend.get_class.return_value = ModelBinder
        # returns an instance of ModelBinder with a new connector_env
        # for the different model
        new_unit = unit.binder_for(model='res.partner')
        self.assertEqual(type(new_unit), ModelBinder)
        self.assertNotEqual(new_unit.connector_env, connector_env)
        self.assertEqual(new_unit.connector_env.model_name, 'res.partner')


class TestConnectorUnitTransaction(common.TransactionCase):

    def test_instance(self):

        class ModelUnit(ConnectorUnit):
            _model_name = 'res.users'

        session = ConnectorSession(self.env.cr, self.env.uid,
                                   context=self.env.context)
        backend_record = mock.Mock(name='BackendRecord')
        backend = mock.Mock(name='Backend')
        backend_record.get_backend.return_value = backend
        connector_env = connector.ConnectorEnvironment(backend_record,
                                                       session,
                                                       'res.users')
        unit = ConnectorUnit(connector_env)
        self.assertEqual(unit.model, self.env['res.users'])
        self.assertEqual(unit.env, self.env)
        self.assertEqual(unit.localcontext, self.env.context)


class TestConnectorEnvironment(unittest2.TestCase):

    def test_create_environment_no_connector_env(self):
        session = mock.MagicMock(name='Session')
        backend_record = mock.Mock(name='BackendRecord')
        backend = mock.Mock(name='Backend')
        backend_record.get_backend.return_value = backend
        model = 'res.user'

        connector_env = ConnectorEnvironment.create_environment(
            backend_record, session, model
        )

        self.assertEqual(type(connector_env), ConnectorEnvironment)

    def test_create_environment_existing_connector_env(self):

        class MyConnectorEnvironment(ConnectorEnvironment):
            _propagate_kwargs = ['api']

            def __init__(self, backend_record, session, model_name, api=None):
                super(MyConnectorEnvironment, self).__init__(backend_record,
                                                             session,
                                                             model_name)
                self.api = api

        session = mock.MagicMock(name='Session')
        backend_record = mock.Mock(name='BackendRecord')
        backend = mock.Mock(name='Backend')
        backend_record.get_backend.return_value = backend
        model = 'res.user'
        api = object()

        cust_env = MyConnectorEnvironment(backend_record, session, model,
                                          api=api)

        new_env = cust_env.create_environment(backend_record, session, model,
                                              connector_env=cust_env)

        self.assertEqual(type(new_env), MyConnectorEnvironment)
        self.assertEqual(new_env.api, api)
