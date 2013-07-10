*****************
Developer's guide
*****************

.. toctree::
   :maxdepth: 2

   guides/overview.rst
   guides/bootstrap_connector.rst

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

