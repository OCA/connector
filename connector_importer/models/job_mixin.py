# -*- coding: utf-8 -*-
# Author: Simone Orsi
# Copyright 2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, api, exceptions, _

from odoo.addons.queue_job.job import DONE, STATES


class JobRelatedMixin(object):
    """Mixin klass for queue.job relationship.

    We do not use an abstract model to be able to not re-define
    the relation on each inheriting model.
    """

    job_id = fields.Many2one(
        'queue.job',
        string='Job',
        readonly=True,
    )
    job_state = fields.Selection(
        STATES,
        string='Job State',
        readonly=True,
        select=True,
        related='job_id.state'
    )

    @api.model
    def has_job(self):
        return bool(self.job_id)

    @api.model
    def job_done(self):
        return self.job_state == DONE

    @api.model
    def check_delete(self):
        if self.has_job() and not self.job_done():
            raise exceptions.Warning(_('You must complete the job first!'))

    @api.multi
    def unlink(self):
        for item in self:
            item.check_delete()
        return super(JobRelatedMixin, self).unlink()
