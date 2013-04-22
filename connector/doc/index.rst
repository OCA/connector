.. Connectors documentation master file, created by
   sphinx-quickstart on Mon Feb  4 11:35:44 2013.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

#################
OpenERP Connector
#################

This is a framework to build connectors between OpenERP and external
systems or services.

OpenERP Connector is mainly developed by the Magentoerpconnect Core
Editors, these being Camptocamp_ and Akretion_. The `source is on
launchpad`_.

This connector is designed to have a strong and efficient core, with the
ability to extend it with extension modules or local customizations.

.. _Camptocamp: http://www.camptocamp.com
.. _Akretion: http://www.akretion.com
.. _`source is on launchpad`: https://code.launchpad.net/openerp-connector


*****************
Developer's guide
*****************

.. toctree::
   :maxdepth: 2

   guides/overview.rst

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

.. todo:: how to contribute, releases notes, license

* how to contribute

* release notes

* license

.. toctree::
   :maxdepth: 1

   project/roadmap
   project/contributors

Concepts
========

Glossary:

.. glossary::

    Job

        A unit of work consisting of a single complete and atomic task.
        Example: import of a product.

    Backend

        An external service on which we connect OpenERP. In the context
        of the Magento connector, Magento is a backend.

    Mapping

        A mapping defines how the data is converted from Magento to
        OpenERP and reversely.

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

