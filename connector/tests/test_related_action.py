# -*- coding: utf-8 -*-

import mock
import unittest

import odoo.tests.common as common
from ..connector import Binder
from ..queue.job import Job, related_action
from ..related_action import unwrap_binding


def task_no_related(env, model_name):
    pass


def task_related_none(env, model_name):
    pass


def task_related_return(env, model_name):
    pass


def task_related_return_kwargs(env, model_name):
    pass


def open_url(env, job, url=None):
    subject = job.args[0]
    return {
        'type': 'ir.actions.act_url',
        'target': 'new',
        'url': url.format(subject=subject),
    }


@related_action(action=open_url, url='https://en.wikipedia.org/wiki/{subject}')
def task_wikipedia(env, subject):
    pass


@related_action(action=unwrap_binding)
def try_unwrap_binding(env, model_name, binding_id):
    pass


class test_related_action(unittest.TestCase):
    """ Test Related Actions """

    def setUp(self):
        super(test_related_action, self).setUp()
        self.env = mock.MagicMock()

    def test_no_related_action(self):
        """ Job without related action """
        job = Job(self.env, func=task_no_related)
        self.assertIsNone(job.related_action(self.env))

    def test_return_none(self):
        """ Job with related action returning None """
        # default action returns None
        job = Job(self.env, func=related_action()(task_related_none))
        self.assertIsNone(job.related_action(self.env))

    def test_return(self):
        """ Job with related action check if action returns correctly """
        def action(env, job):
            return env, job
        job = Job(self.env,
                  func=related_action(action=action)(task_related_return))
        act_env, act_job = job.related_action(self.env)
        self.assertEqual(act_env, self.env)
        self.assertEqual(act_job, job)

    def test_kwargs(self):
        """ Job with related action check if action propagates kwargs """
        def action(env, job, a=1, b=2):
            return a, b
        task = task_related_return_kwargs
        job_func = related_action(action=action, b=4)(task)
        job = Job(self.env, func=job_func)
        self.assertEqual(job.related_action(self.env), (1, 4))

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


class test_related_action_storage(common.TransactionCase):
    """ Test related actions on stored jobs """

    def setUp(self):
        super(test_related_action_storage, self).setUp()
        self.queue_job = self.env['queue.job']

    def test_store_related_action(self):
        """ Call the related action on the model """
        job = Job(self.env, func=task_wikipedia, args=('Discworld',))
        job.store()
        stored_job = self.queue_job.search([('uuid', '=', job.uuid)])
        self.assertEqual(len(stored_job), 1)
        expected = {'type': 'ir.actions.act_url',
                    'target': 'new',
                    'url': 'https://en.wikipedia.org/wiki/Discworld',
                    }
        self.assertEquals(stored_job.open_related_action(), expected)

    def test_unwrap_binding_not_exists(self):
        """ Call the related action on the model on non-existing record """
        job = Job(self.env, func=try_unwrap_binding, args=('res.users', 555))
        job.store()
        stored_job = self.queue_job.search([('uuid', '=', job.uuid)])
        stored_job.unlink()
        self.assertFalse(stored_job.exists())
        self.assertEquals(unwrap_binding(self.env, job), None)

    def test_related_action_model_method(self):
        """ Related action on model method """
        # try:
        related_action(action=task_related_return)(
            self.env['res.users'].preference_save
        )
        self.assertEquals(
            self.env['res.users'].preference_save.related_action,
            task_related_return
        )
        # TODO
        # finally:
        #     method = self.env['res.users'].preference_save
        #     if hasattr(method.__func__.related_action):
        #         import pdb; pdb.set_trace()
        #         del method.__func__.related_action
