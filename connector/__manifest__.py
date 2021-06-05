# -*- coding: utf-8 -*-
# Copyright 2013-2017 Camptocamp SA
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html)

{'name': 'Connector',
 'version': '10.0.2.1.1',
 'author': 'Camptocamp,Openerp Connector Core Editors,'
           'Odoo Community Association (OCA)',
 'website': 'http://odoo-connector.com',
 'license': 'LGPL-3',
 'category': 'Generic Modules',
 'depends': ['mail',
             'queue_job',
             'component',
             'component_event',
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
