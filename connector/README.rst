.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
    :alt: License

Connector
=========

This is a framework designed to build connectors with external systems,
usually called `Backends` in the documentation.

Documentation: http://odoo-connector.com

It features:

* A jobs queue

    In which the connectors can push functions (synchronization tasks)
    to be executed later.

* An event pattern

    The connectors can subscribe listener functions on the events,
    executed when the events are fired.

* Connector base classes

    Called ``ConnectorUnit``.

    Include base classes for the use in connectors, ready to be extended:

    * ``Synchronizer``: flow of an import or export
    * ``Mapper``: transform a record according to mapping rules
    * ``Binder``: link external IDs with local IDS
    * ``BackendAdapter``: adapter interface for the exchanges with the backend
    * But ``ConnectorUnit`` can be extended to accomplish any task

* A multi-backend support

    Each ``ConnectorUnit`` can be registered amongst a backend type (eg.
    Magento) and a backend version (allow to have a different ``Mapper``
    for each backend's version for instance)

It is used for example used to connect Magento_ and Prestashop_, but
also used with Solr, CMIS, ...

.. _Magento: http://odoo-magento-connector.com
.. _Prestashop: https://github.com/OCA/connector-prestashop

Configuration and usage
=======================

This module does nothing on its own.  It is a ground for developing
advanced connector modules. For further information, please go on:
http://odoo-connector.com

Credits
=======

Contributors
------------

Read the `contributors list`_

.. _contributors list: ./AUTHORS

Maintainer
----------

.. image:: http://odoo-community.org/logo.png
   :alt: Odoo Community Association
   :target: http://odoo-community.org

This module is maintained by the OCA.

OCA, or the Odoo Community Association, is a nonprofit organization whose mission is to support the collaborative development of Odoo features and promote its widespread use.

To contribute to this module, please visit http://odoo-community.org.
