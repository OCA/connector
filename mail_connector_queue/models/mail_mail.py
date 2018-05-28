# -*- coding: utf-8 -*-
# Copyright 2018 ACSONE SA/NV
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from openerp import fields, models


class MailMail(models.Model):

    _inherit = 'mail.mail'

    mail_job_priority = fields.Integer(oldname='priority')
