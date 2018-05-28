# -*- coding: utf-8 -*-
# Copyright 2018 ACSONE SA/NV
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': 'Mail Connector Queue',
    'summary': """
        Email Connector Queue""",
    'version': '8.0.1.0.1',
    'license': 'AGPL-3',
    'author': 'ACSONE SA/NV,Odoo Community Association (OCA)',
    'website': 'https://github.com/OCA/connector',
    'depends': [
        'connector',
        'mail',
    ],
    'data': [
        'views/mail_mail.xml',
    ],
    'demo': [
    ],
    'post_init_hook': 'post_init_hook',
    'uninstall_hook': 'uninstall_hook',
}
