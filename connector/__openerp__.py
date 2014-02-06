# -*- coding: utf-8 -*-
##############################################################################
#
#    Author: Guewen Baconnier
#    Copyright 2013-2014 Camptocamp SA
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
 'version': '2.1.1',
 'author': 'Openerp Connector Core Editors',
 'website': 'http://openerp-connector.com',
 'license': 'AGPL-3',
 'category': 'Generic Modules',
 'description': """
Connector
=========

This is a framework designed to build connectors with external systems,
usually called `Backends`.

Documentation: http://openerp-connector.com

It features:

* A jobs queue

    In which the connectors can push functions (synchronization tasks)
    to be executed later.

* An event pattern

    The connectors can subscribe consumer methods, executed when the events
    are fired.

* Connector base classes

    Called ``ConnectorUnit``.

    Include base classes for the use in connectors, ready to be extended:

    * ``Synchronizer``: flow of an import or export
    * ``Mapper``: transform a record according to mapping rules
    * ``Binder``: link external IDs with local IDS
    * ``BackendAdapter``: adapter interface for the exchanges with the backend

* A multi-backend support

    Each ``ConnectorUnit`` can be registered amongst a backend type (eg.
    Magento) or a backend version only.

It is actually used to connect Magento_ and Prestashop_

.. _Magento: http://openerp-magento-connector.com
.. _Prestashop: https://launchpad.net/prestashoperpconnect
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
