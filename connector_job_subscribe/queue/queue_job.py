# -*- coding: utf-8 -*-
# Copyright 2016-2017 Cédric Pigeon
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class QueueJob(models.Model):
    _inherit = 'queue.job'

    @api.multi
    def _subscribe_users_domain(self):
        domain = super(QueueJob, self)._subscribe_users_domain()
        domain.append(('subscribe_job', '=', True))
        return domain
