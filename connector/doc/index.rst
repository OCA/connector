.. Connectors documentation master file, created by
   sphinx-quickstart on Mon Feb  4 11:35:44 2013.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

#####
About
#####

This is a framework to build connectors between OpenERP and external
systems or services.

OpenERP Connector has been developed by Camptocamp_ and is maintained
by Camptocamp_, Akretion_ and several contributors.

The `source is on launchpad`_.

This connector is designed to have a strong and efficient core, with the
ability to extend it with extension modules for new features or customizations.

.. _Camptocamp: http://www.camptocamp.com
.. _Akretion: http://www.akretion.com
.. _`source is on launchpad`: https://code.launchpad.net/openerp-connector

This project is:

*****************
Developer's guide
*****************

.. toctree::
   :maxdepth: 2

   guides/overview.rst
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

.. todo:: how to contribute, releases notes, license
=======
 * An addon to install in OpenERP;
 * A framework for the creation of connectors between OpenERP and other
   systems;
 * Open-Source (AGPL version 3).

It is not:

 * Built for real-time exchanges;
 * An standalone application.

Why should I use it?
====================

 *


Services
========

Companies offering services:

.. image:: _static/img/c2c_square_baseline_192.jpg
   :alt: Camptocamp
   :target: Camptocamp_

.. image:: _static/img/akretion_logo.png
   :alt: Akretion
   :target: Akretion_
