# -*- coding: utf-8 -*-

import mock
import unittest

import odoo.tests.common as common
from odoo.addons.queue_job.job import Job, related_action
from odoo.addons.connector.connector import Binder
from ..related_action import unwrap_binding


@related_action(action=unwrap_binding)
def try_unwrap_binding(env, model_name, binding_id):
    pass


class TestRelatedActionBinding(unittest.TestCase):
    """ Test Related Actions with Bindings """

    def setUp(self):
        super(TestRelatedActionBinding, self).setUp()
        self.env = mock.MagicMock()

    def test_unwrap_binding(self):
        """ Call the unwrap binding related action """
        class TestBinder(Binder):
            _model_name = 'binding.res.users'

            def unwrap_binding(self, binding_id, browse=False):
                return 42

            def unwrap_model(self):
                return 'res.users'

        job = Job(self.env, func=try_unwrap_binding, args=('res.users', 555))
        env = mock.MagicMock(name='env')
        backend_record = mock.Mock(name='backend_record')
        backend = mock.Mock(name='backend')
        browse_record = mock.Mock(name='browse_record')
        backend.get_class.return_value = TestBinder
        backend_record.get_backend.return_value = backend
        browse_record.exists.return_value = True
        browse_record.backend_id = backend_record
        recordset = mock.Mock(name='recordset')
        env.__getitem__.return_value = recordset
        recordset.browse.return_value = browse_record
        action = unwrap_binding(env, job)
        expected = {
            'name': mock.ANY,
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_id': 42,
            'res_model': 'res.users',
        }
        self.assertEquals(action, expected)

    def test_unwrap_binding_direct_binding(self):
        """ Call the unwrap binding related action """
        class TestBinder(Binder):
            _model_name = 'res.users'

            def unwrap_binding(self, binding_id, browse=False):
                raise ValueError('Not an inherits')

            def unwrap_model(self):
                raise ValueError('Not an inherits')

        job = Job(self.env, func=try_unwrap_binding, args=('res.users', 555))
        env = mock.MagicMock(name='env')
        backend_record = mock.Mock(name='backend_record')
        backend = mock.Mock(name='backend')
        browse_record = mock.Mock(name='browse_record')
        backend.get_class.return_value = TestBinder
        backend_record.get_backend.return_value = backend
        browse_record.exists.return_value = True
        browse_record.backend_id = backend_record
        recordset = mock.Mock(name='recordset')
        env.__getitem__.return_value = recordset
        recordset.browse.return_value = browse_record
        action = unwrap_binding(env, job)
        expected = {
            'name': mock.ANY,
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_id': 555,
            'res_model': 'res.users',
        }
        self.assertEquals(action, expected)


class TestRelatedActionStorageBinding(common.TransactionCase):
    """ Test related actions on stored jobs """

    def test_unwrap_binding_not_exists(self):
        """ Call the related action on the model on non-existing record """
        job = Job(self.env, func=try_unwrap_binding, args=('res.users', 555))
        job.store()
        stored_job = self.env['queue.job'].search([('uuid', '=', job.uuid)])
        stored_job.unlink()
        self.assertFalse(stored_job.exists())
        self.assertEquals(unwrap_binding(self.env, job), None)
