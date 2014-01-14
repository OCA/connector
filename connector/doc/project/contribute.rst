.. _contribute:

##########
Contribute
##########

We accept with pleasure all type of contributions:

* bug reports
* merge proposals
* ideas
* translations
* ...

Have a look on the :ref:`Magento Connector Developer's Guide
<connectormagento:contribute>` which is more complete, most of the
information is the same.

The Launchpad project is: http://launchpad.net/openerp-connector

*****************************
Want to start a new connector
*****************************

If you want to start a new connector based on the framework,
a sane approach is to read this documentation, especially
:ref:`concepts` and :ref:`bootstrap-connector`.

Then, my personal advice is to look at the existing connectors (`OpenERP
Magento Connector`_, `OpenERP Prestashop Connector`_). You will also probably
need to dive a bit in the framework's code.

If the connector belongs to the e-commerce domain, you may want to reuse the pieces
of the `E-Commerce Connector`_ module.

.. _naming-convention:

Naming conventions
==================

The naming conventions for the new projects are the following:

Name of the project
    openerp-connector-xxx

Name of the OpenERP module:
    connector_xxx

Example:
    http://launchpad.net/openerp-connector-magento

    ``connector_magento``

Actually, the Magento and Prestashop connectors do not respect this convention
for historical reasons (magentoerpconnect, prestashoperpconnect).
New projects should ideally respect it.

.. _`OpenERP Magento Connector`: https://code.launchpad.net/openerp-connector-magento
.. _`OpenERP Prestashop Connector`: https://code.launchpad.net/prestashoperpconnect
.. _`E-Commerce Connector`: https://code.launchpad.net/openerp-connector-ecommerce
