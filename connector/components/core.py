# -*- coding: utf-8 -*-
# Copyright 2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo.addons.component.core import AbstractComponent
from odoo.addons.queue_job.exception import RetryableJobError
from ..connector import pg_try_advisory_lock


class BaseConnectorComponent(AbstractComponent):

    _name = 'base.connector'
    _inherit = None
    _collection = None
    _apply_on = None
    _usage = None

    @property
    def backend_record(self):
        # backward compatibility
        return self.work.collection

    def binder_for(self, model=None):
        """ Returns an new instance of the correct ``Binder`` for
        a model """
        return self.components(usage='binder', model_name=model)

    def advisory_lock_or_retry(self, lock, retry_seconds=1):
        """ Acquire a Postgres transactional advisory lock or retry job

        When the lock cannot be acquired, it raises a
        ``RetryableJobError`` so the job is retried after n
        ``retry_seconds``.

        Usage example:

        ::

            lock_name = 'import_record({}, {}, {}, {})'.format(
                self.backend_record._name,
                self.backend_record.id,
                self.model._name,
                self.external_id,
            )
            self.advisory_lock_or_retry(lock_name, retry_seconds=2)

        See :func:``odoo.addons.connector.connector.pg_try_advisory_lock``
        for details.

        :param lock: The lock name. Can be anything convertible to a
           string.  It needs to represent what should not be synchronized
           concurrently, usually the string will contain at least: the
           action, the backend type, the backend id, the model name, the
           external id
        :param retry_seconds: number of seconds after which a job should
           be retried when the lock cannot be acquired.
        """
        if not pg_try_advisory_lock(self.env, lock):
            raise RetryableJobError('Could not acquire advisory lock',
                                    seconds=retry_seconds,
                                    ignore_retry=True)
