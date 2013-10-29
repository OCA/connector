.. Connectors documentation master file, created by
   sphinx-quickstart on Mon Feb  4 11:35:44 2013.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

#################
OpenERP Connector
#################

OpenERP Connector is a powerful and generic framework to develop any kind of
bi-directional connector between OpenERP (Open Source ERP) and any other
software or service. It is installed as a normal addons in OpenERP.

It is designed to have a modular and generic core, with the ability to be
extended with additional modules for new features or customizations.

The development of OpenERP Connector has been started by `Camptocamp`_ and is now
maintained by `Camptocamp`_, `Akretion`_ and several :ref:`contributors`.

Subscribe now to the `project's mailing list`_!

Core Features
=============

* **100% Open Source** (`AGPL version 3`_): the full `source code is available
  on Launchpad`_
* Not only designed to connect OpenERP with e-commerce backends,
  rather it is **adaptable** to connect OpenERP with any type of service.
* **Robust for high volumetries** and **easy to monitor** thanks to a :ref:`jobs-queue`.
* A flexible set of building blocks, it does not force to a certain
  implementation but leaves the final choice to the
  developer on how to use the proposed pieces.
* See a :ref:`code-overview` with examples of code

.. _Camptocamp: http://www.camptocamp.com
.. _Akretion: http://www.akretion.com
.. _`source code is available on Launchpad`: https://code.launchpad.net/openerp-connector
.. _`AGPL version 3`: http://www.gnu.org/licenses/agpl-3.0.html
.. _`project's mailing list`: https://launchpad.net/~openerp-connector-community

Connectors based on the framework
=================================

* `Magento Connector <http://www.openerp-magento-connector.com>`_
* `Prestashop Connector <https://launchpad.net/prestashoperpconnect>`_
* Develop easily and rapidly your own connector based on this powerful
  framework and list your project on this page! Examples:

  * E-Commerce: OpenERP OsCommerce connector, OpenERP Drupal Commerce connector, OpenERP Spree connector, OpenERP Ebay connector, OpenERP Amazon connector…
  * CMS: OpenERP Wordpress connector…
  * CRM: OpenERP SugarCRM connector, OpenERP Zabbix connector…
  * Project Management: OpenERP Redmine connector…
  * Ticketing: OpenERP Request Tracker connector, OpenERP GLPI connector…

Top financial contributors
==========================

.. image:: _static/img/LogicSupply_Orange_260x80_transparent.png
   :alt: Logic Supply
   :target: http://www.logicsupply.com

.. image:: _static/img/logo-debonix.jpg
   :alt: Debonix
   :target: http://www.debonix.fr

|
*See all the project's* :ref:`financial-contributors`.

Companies offering services
===========================

.. image:: _static/img/c2c_square_baseline_192.jpg
   :alt: Camptocamp
   :target: Camptocamp_

.. image:: _static/img/akretion_logo.png
   :alt: Akretion
   :target: Akretion_


*****************
Developer's guide
*****************

.. toctree::
   :maxdepth: 2

   guides/code_overview.rst
   guides/concepts.rst
   guides/bootstrap_connector.rst
   guides/multiprocessing.rst

API Reference
=============

.. toctree::
   :maxdepth: 1

   api/api_connector.rst
   api/api_session.rst
   api/api_backend.rst
   api/api_event.rst
   api/api_binder.rst
   api/api_mapper.rst
   api/api_synchronizer.rst
   api/api_backend_adapter.rst
   api/api_queue.rst
   api/api_exception.rst

Project
=======

.. toctree::
   :maxdepth: 1

   project/contribute
   project/contributors
   project/license
   project/changes
   project/roadmap

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
