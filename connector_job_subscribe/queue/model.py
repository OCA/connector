# -*- coding: utf-8 -*-
# Copyright 2016 Cédric Pigeon
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from openerp import api, models


class QueueJob(models.Model):
    _inherit = 'queue.job'

    @api.multi
    def _get_subscribe_users_domain(self):
        domain = super(QueueJob, self)._get_subscribe_users_domain()
        domain.append(('subscribe_job', '=', True))
        return domain
