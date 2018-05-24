# -*- coding: utf-8 -*-
# Copyright 2018 ACSONE SA/NV
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from openerp import SUPERUSER_ID


def _set_mail_cron_state(cr, registry, active):
    cron = registry['ir.model.data'].xmlid_to_object(
        cr, SUPERUSER_ID, 'mail.ir_cron_mail_scheduler_action')
    if cron:
        cron.write({'active': active})


def post_init_hook(cr, registry):
    _set_mail_cron_state(cr, registry, active=False)


def uninstall_hook(cr, registry):
    _set_mail_cron_state(cr, registry, active=True)
