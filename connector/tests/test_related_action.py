# -*- coding: utf-8 -*-

import mock
import unittest2

import openerp
import openerp.tests.common as common
from openerp.addons.connector.queue.job import (
    Job,
    OpenERPJobStorage,
    related_action)
from openerp.addons.connector.session import (
    ConnectorSession)


def task_no_related(session, model_name):
    pass


def task_related_none(session, model_name):
    pass


def task_related_return(session, model_name):
    pass


def task_related_return_kwargs(session, model_name):
    pass


def open_url(session, job, url=None):
    subject = job.args[0]
    return {
        'type': 'ir.actions.act_url',
        'target': 'new',
        'url': url.format(subject=subject),
    }


@related_action(action=open_url, url='https://en.wikipedia.org/wiki/{subject}')
def task_wikipedia(session, subject):
    pass


class test_related_action(unittest2.TestCase):
    """ Test Related Actions """

    def setUp(self):
        super(test_related_action, self).setUp()
        self.session = mock.MagicMock()

    def test_no_related_action(self):
        """ Job without related action """
        job = Job(func=task_no_related)
        self.assertIsNone(job.related_action(self.session))

    def test_return_none(self):
        """ Job with related action returning None """
        # default action returns None
        job = Job(func=related_action()(task_related_none))
        self.assertIsNone(job.related_action(self.session))

    def test_return(self):
        """ Job with related action check if action returns correctly """
        def action(session, job):
            return session, job
        job = Job(func=related_action(action=action)(task_related_return))
        act_session, act_job = job.related_action(self.session)
        self.assertEqual(act_session, self.session)
        self.assertEqual(act_job, job)

    def test_kwargs(self):
        """ Job with related action check if action propagates kwargs """
        def action(session, job, a=1, b=2):
            return a, b
        job_func = related_action(action=action, b=4)(task_related_return_kwargs)
        job = Job(func=job_func)
        self.assertEqual(job.related_action(self.session), (1, 4))


class test_related_action_storage(common.TransactionCase):
    """ Test related actions on stored jobs """

    def setUp(self):
        super(test_related_action_storage, self).setUp()
        self.pool = openerp.modules.registry.RegistryManager.get(common.DB)
        self.session = ConnectorSession(self.cr, self.uid)
        self.queue_job = self.registry('queue.job')

    def test_store_related_action(self):
        """ Call the related action on the model """
        job = Job(func=task_wikipedia, args=('Discworld',))
        storage = OpenERPJobStorage(self.session)
        storage.store(job)
        stored_ids = self.queue_job.search(self.cr, self.uid,
                                           [('uuid', '=', job.uuid)])
        self.assertEqual(len(stored_ids), 1)
        stored = self.queue_job.browse(self.cr, self.uid, stored_ids[0])
        expected = {'type': 'ir.actions.act_url',
                    'target': 'new',
                    'url': 'https://en.wikipedia.org/wiki/Discworld',
                    }
        self.assertEquals(stored.open_related_action(), expected)
