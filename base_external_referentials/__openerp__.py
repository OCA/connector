# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution    
#    Copyright (C) 2009 Akretion (<http://www.akretion.com>). All Rights Reserved
#    authors: Raphaël Valyi, Sharoon Thomas
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################


{
    'name': 'Base External Referentials',
    'version': '1.0',
    'category': 'Generic Modules/Base',
    'description': """
This module provide an abstract common minimal base to add any additional external id columns
to some OpenObject table, pointing to some external referential.
A referential is abstract and minimal at this stage, it only has:
* a name
* a location (possibly webservice URL, database connection URL...); the connection method will tell it...
* referential credentials (user name + password)
* placeholders for custom in and out mapping for OpenERP object fields.

OpenERP already has limited supported to external ids using the ir_model_data and the id
fields in the loaded data such as XML or CSV. We think that's OK to store all referential ids
into the same ir_model_data table: yes it makes it large, but synchronisation operations involve
a network bottleneck anyway, so it's largely OK and negligible to have a large table here.
The existing ir_model_data feature of OpenERP is mostly thought as an mono-external referential
(even if the module key of ir_model_data plays some referential scoping role). Here we just push
the concept further to assume multiple external ids for OpenERP entities and add the possibility
to customize their field mapping directly in OpenERP to accomodate the external systems.
    """,
    'author': 'Raphaël Valyi (Akretion.com), Sharoon Thomas (Openlabs.co.in)',
    'website': 'http://www.akretion.com, http://openlabs.co.in/',
    'depends': ['base'],
    'init_xml': [],
    'update_xml': ['base_external_referentials_view.xml',
                   'report_view.xml',
                   'base_external_referentials_menu.xml',],
    'demo_xml': [],
    'installable': True,
    'certificate': '',
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
