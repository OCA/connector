# -*- coding: utf-8 -*-
# Copyright 2016 Camptocamp
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import models, api
from ..job import DelayableRecordset


class Base(models.AbstractModel):
    """ The base model, which is implicitly inherited by all models. """
    _inherit = 'base'

    @api.multi
    def with_delay(self, priority=None, eta=None,
                   max_retries=None, description=None):
        """ Return a ``DelayableRecordset``

        The returned instance allow to enqueue any method of the recordset's
        Model which is decorated by :func:`~odoo.addons.queue_job.job.job`.

        Usage::

            self.env['res.users'].with_delay().write({'name': 'test'})

        In the line above, in so far ``write`` is allowed to be delayed with
        ``@job``, the write will be executed in an asynchronous job.


        :param priority: Priority of the job, 0 being the higher priority.
                         Default is 10.
        :param eta: Estimated Time of Arrival of the job. It will not be
                    executed before this date/time.
        :param max_retries: maximum number of retries before giving up and set
                            the job state to 'failed'. A value of 0 means
                            infinite retries.  Default is 5.
        :param description: human description of the job. If None, description
                            is computed from the function doc or name
        :return: instance of a DelayableRecordset
        :rtype: :class:`odoo.addons.queue_job.job.DelayableRecordset`

        """
        return DelayableRecordset(self, priority=priority,
                                  eta=eta,
                                  max_retries=max_retries,
                                  description=description)
