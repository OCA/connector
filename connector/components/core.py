# -*- coding: utf-8 -*-
# Copyright 2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

"""

Base Component
==============

The connector proposes a 'base' Component, which can be used in
the ``_inherit`` of your own components.  This is not a
requirement.  It is already inherited by every component
provided by the Connector.


"""

from odoo.addons.component.core import AbstractComponent
from odoo.addons.queue_job.exception import RetryableJobError
from ..connector import pg_try_advisory_lock


class BaseConnectorComponent(AbstractComponent):
    """ Base component for the connector

    Is inherited by every components of the Connector (Binder, Mapper, ...)
    and adds a few methods which are of common usage in the connectors.

    """

    _name = 'base.connector'

    @property
    def backend_record(self):
        """ Backend record we are working with """
        # backward compatibility
        return self.work.collection

    def binder_for(self, model=None):
        """ Shortcut to get Binder for a model

        Equivalent to: ``self.component(usage='binder', model_name='xxx')``

        """
        return self.component(usage='binder', model_name=model)

    def advisory_lock_or_retry(self, lock, retry_seconds=1):
        """ Acquire a Postgres transactional advisory lock or retry job

        When the lock cannot be acquired, it raises a
        :exc:`odoo.addons.queue_job.exception.RetryableJobError` so the job
        is retried after n ``retry_seconds``.

        Usage example:

        .. code-block:: python

            lock_name = 'import_record({}, {}, {}, {})'.format(
                self.backend_record._name,
                self.backend_record.id,
                self.model._name,
                self.external_id,
            )
            self.advisory_lock_or_retry(lock_name, retry_seconds=2)

        See :func:`odoo.addons.connector.connector.pg_try_advisory_lock` for
        details.

        :param lock: The lock name. Can be anything convertible to a
           string.  It needs to represent what should not be synchronized
           concurrently, usually the string will contain at least: the
           action, the backend name, the backend id, the model name, the
           external id
        :param retry_seconds: number of seconds after which a job should
           be retried when the lock cannot be acquired.
        """
        if not pg_try_advisory_lock(self.env, lock):
            raise RetryableJobError('Could not acquire advisory lock',
                                    seconds=retry_seconds,
                                    ignore_retry=True)
