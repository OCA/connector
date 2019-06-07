# -*- coding: utf-8 -*-
# Copyright 2013-2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

{'name': 'Connector',
 'version': '12.0.1.1.0',
 'author': 'Camptocamp,Openerp Connector Core Editors,'
           'Odoo Community Association (OCA)',
 'website': 'http://odoo-connector.com',
 'license': 'AGPL-3',
 'category': 'Generic Modules',
 'depends': ['mail',
             'queue_job',
             'component',
             'component_event',
             ],
 'data': ['security/connector_security.xml',
          'security/ir.model.access.csv',
          'views/checkpoint_views.xml',
          'views/connector_menu.xml',
          'views/res_partner_views.xml',
          ],
 'installable': True,
 }
