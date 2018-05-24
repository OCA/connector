# -*- coding: utf-8 -*-
# Copyright 2018 ACSONE SA/NV
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from openerp.addons.connector.event import on_record_create
from openerp.addons.connector.queue.job import job


@job
def send_mail(session, mail_id):
    mail = session.env['mail.mail'].browse(mail_id)
    if not mail.exists():
        return "mail.mail record (id=%s) no longer exists" % mail_id
    elif mail.state != 'outgoing':
        return "Not in Outgoing state, ignoring"
    else:
        mail.send(auto_commit=False, raise_exception=True)


@on_record_create(model_names='mail.mail')
def mail_creation(session, model_name, record_id, vals):
    kwargs = {}
    if 'priority' in vals:
        kwargs['priority'] = vals['priority']
    send_mail.delay(session, record_id, **kwargs)
