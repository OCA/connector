# -*- encoding: utf-8 -*-
###############################################################################
#                                                                             #
#   file_exchange for OpenERP                                                 #
#   Copyright (C) 2012 Akretion Emmanuel Samyn <emmanuel.samyn@akretion.com>  #
#                                                                             #
#   This program is free software: you can redistribute it and/or modify      #
#   it under the terms of the GNU Affero General Public License as            #
#   published by the Free Software Foundation, either version 3 of the        #
#   License, or (at your option) any later version.                           #
#                                                                             #
#   This program is distributed in the hope that it will be useful,           #
#   but WITHOUT ANY WARRANTY; without even the implied warranty of            #
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the             #
#   GNU Affero General Public License for more details.                       #
#                                                                             #
#   You should have received a copy of the GNU Affero General Public License  #
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.     #
#                                                                             #
###############################################################################

{
    'name': 'file_exchange',
    'version': '6.1.0',
    'category': 'Generic Modules/Others',
    'license': 'AGPL-3',
    'description': """
Definition : a file exchange is a file to be exchanged (in/out) between OpenERP and another system (referential)
Goal : store file details and and file fields
""",
    'author': 'Akretion',
    'website': 'http://www.akretion.com/',
    'depends': ['base_scheduler_creator', 'base_external_file_protocole'], 
    'init_xml': [],
    'update_xml': [ 
        'file_exchange_view.xml',
        'file_exchange_menu.xml',
        'settings/external.referential.category.csv',
        'settings/external.referential.type.csv',
        'security/file_exchange_security.xml',
        'security/file_exchange_security.xml',
        'security/ir.model.access.csv',
    ],
    'demo_xml': [],
    'installable': True,
    'active': False,
}

