# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)


{'name': 'Job Queue',
 'version': '10.0.1.0.0',
 'author': 'Camptocamp,Acsone,Odoo Community Association (OCA)',
 'website': 'http://odoo-connector.com',
 'license': 'AGPL-3',
 'category': 'Generic Modules',
 'depends': ['mail'
             ],
 'external_dependencies': {'python': ['requests'
                                      ],
                           },
 'data': ['security/security.xml',
          'security/ir.model.access.csv',
          'views/queue_job_views.xml',
          'data/queue_data.xml',
          ],
 'installable': True,
 'application': True,
 }
