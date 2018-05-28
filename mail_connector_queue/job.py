# -*- coding: utf-8 -*-
# Copyright 2018 ACSONE SA/NV
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from openerp.addons.connector.event import on_record_create, on_record_write
from openerp.addons.connector.queue.job import job


@job
def send_mail(session, mail_id):
    # make sure two jobs don't send the same email
    session.cr.execute(
        "SELECT id FROM mail_mail WHERE id = %s FOR UPDATE", (mail_id,))

    mail = session.env['mail.mail'].browse(mail_id)
    if not mail.exists():
        return "mail.mail record (id=%s) no longer exists" % mail_id
    elif mail.state != 'outgoing':
        return "Not in Outgoing state, ignoring"
    else:
        mail.send(auto_commit=False, raise_exception=True)


def queue_job(session, record_id, vals):
    kwargs = {}
    record = session.env['mail.mail'].browse(record_id)
    if record.mail_job_priority:
        kwargs['priority'] = record.mail_job_priority
    send_mail.delay(session, record_id, **kwargs)


@on_record_create(model_names='mail.mail')
def mail_creation(session, model_name, record_id, vals):
    if vals.get('state', 'outgoing') == 'outgoing':
        queue_job(session, record_id, vals)


@on_record_write(model_names='mail.mail')
def mail_write(session, model_name, record_id, vals):
    if vals.get('state') == 'outgoing':
        queue_job(session, record_id, vals)
