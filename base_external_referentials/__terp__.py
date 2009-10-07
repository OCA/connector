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
A referential is abstract and minimal at this stage, it's only identified
by:
* a name
* a location (possibly webservice URL, database connection URL...); the connection method will tell it...
* referential credentials (user name + password)

OpenERP already has limited supported to external ids using the ir_model_data and the id
fields in the loaded data such as XML or CSV.
The issue is that teh current system, while very useful to deal with internal OpenERP data has some
limitations:
* it doesn't scale well to whole production data because everything ends up into the ir_model_data
* all the system is built with a using reference id in mind. But in fact you might want SEVERAL external ids.
Say you sale your products over several websites (using the new Magento multi-instance connector for
instance), then you want that each product have SEVERAL external id columns. This is exactly what
this module enables!
    """,
    'author': 'Raphaël Valyi (Akretion.com), Sharoon Thomas (Openlabs.co.in)',
    'website': 'http://www.akretion.com',
    'depends': ['base'],
    'init_xml': [],
    'update_xml': ['base_external_referentials_view.xml'],
    'demo_xml': [],
    'installable': True,
    'certificate': '',
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
