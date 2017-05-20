# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (C) 2017 Camptocamp
#
##############################################################################
{
    'name': 'Connector Importer',
    'description': """This module takes care of import sessions.""",
    'version': '10.0.1.0.0',
    'depends': [
        'connector',
    ],
    'author': 'Camptocamp',
    'license': 'AGPL-3',
    'category': 'Uncategorized',
    'website': 'http://www.camptocamp.com',
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/import_backend_views.xml',
        'views/import_recordset_views.xml',
        # TODO
        # 'views/import_user_views.xml',
        'views/web_report_template.xml',
        # TODO
        # 'wizards/base.xml',
        # 'wizards/products/wizard_import_products.xml',
        'menuitems.xml',
    ],
    'external_dependencies': {'python': ['chardet']},
}
