# -*- coding: utf-8 -*-
# Copyright 2013-2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

{'name': 'Connector',
 'version': '10.0.1.0.0',
 'author': 'Camptocamp,Openerp Connector Core Editors,'
           'Odoo Community Association (OCA)',
 'website': 'http://odoo-connector.com',
 'license': 'AGPL-3',
 'category': 'Generic Modules',
 'depends': ['mail',
             'queue_job',
             ],
 'data': ['security/connector_security.xml',
          'security/ir.model.access.csv',
          'checkpoint/checkpoint_view.xml',
          'connector_menu.xml',
          'setting_view.xml',
          'res_partner_view.xml',
          ],
 'installable': True,
 }
