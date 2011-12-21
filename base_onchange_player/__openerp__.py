# -*- encoding: utf-8 -*-
#################################################################################
#                                                                               #
#    base_onchange_player for OpenERP                                           #
#    Copyright (C) 2011 Akretion Sébastien BEAU <sebastien.beau@akretion.com>   #
#                                                                               #
#    This program is free software: you can redistribute it and/or modify       #
#    it under the terms of the GNU Affero General Public License as             #
#    published by the Free Software Foundation, either version 3 of the         #
#    License, or (at your option) any later version.                            #
#                                                                               #
#    This program is distributed in the hope that it will be useful,            #
#    but WITHOUT ANY WARRANTY; without even the implied warranty of             #
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the              #
#    GNU Affero General Public License for more details.                        #
#                                                                               #
#    You should have received a copy of the GNU Affero General Public License   #
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.      #
#                                                                               #
#################################################################################


{
    'name': 'base_onchange_player',
    'version': '0.1',
    'category': 'ORM Extention',
    'license': 'AGPL-3',
    'description': """This module give the possibility to call onchange method easily in your code, it's just an Abstract Module that add some abstraction when you need to call onchange method.
        A sample of call is done in the module base_sale_multichannels
        """,
    'author': 'Akretion',
    'website': 'http://www.akretion.com/',
    'depends': ['base'], 
    'init_xml': [],
    'update_xml': [
    ],
    'demo_xml': [],
    'installable': True,
    'active': False,
}

