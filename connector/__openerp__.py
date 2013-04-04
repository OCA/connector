# -*- coding: utf-8 -*-
##############################################################################
#
#    Author: Guewen Baconnier
#    Copyright 2013 Camptocamp SA
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

{'name': 'Connector',
 'version': '2.0.0',
 'author': 'Magentoerpconnect Core Editors',
 'website': 'http://www.magentoerpconnect.com',
 'license': 'AGPL-3',
 'category': 'Generic Modules',
 'description': """
Connector
=========

TODO
----

Write a good presentation of the framework.


previous description
--------------------

Definition : a referential is an external system that will interacts with OpenERP
Goal : store external system connection details and objects fields mapping

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
 'depends': ['mail'
             ],
 'data': ['security/connector_security.xml',
          'security/ir.model.access.csv',
          'queue/model_view.xml',
          'queue/queue_data.xml',
          'checkpoint/checkpoint_view.xml',
          'connector_menu.xml',
          'setting_view.xml',
          'res_partner_view.xml',
          ],
 'installable': True,
 'application': True,
}
