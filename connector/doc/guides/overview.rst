.. _connectors-specifications:

##################
Connector Overview
##################

The framework to develop connectors is decoupled in small pieces of
codes interacting together. Each of them can be used or not in an
implementation.

An example of implementation is Magentoerpconnect_.

This document describes them from a high-level point of view and gives
pointers to more concrete 'how-to' or small tutorials.

.. _Magentoerpconnect: http://code.launchpad.net/magentoerpconnect

******
Events
******

Events are hooks in OpenERP on which we can plug some actions. They are
based on an Observer pattern.

The basic idea is to declare an :py:class:`~connector.event.Event`, for
instance :py:class:`~connector.event.on_record_create`.
Then each connector has the ability to subscribe one or many function on it.
The creation of a record should fire
:py:class:`~connector.event.on_record_create`,
which will trigger all the subscribed functions.

The same event can be shared across several connectors, easing their
implementation.
For instance, the module connector_ecommerce_ which extends the
framework with common e-commerce capabilities, adds its own events
common to e-commerce.

A connectors developer is mostly interested by:

.. todo:: add pointers

* register a new function on an event
* unregister a function from an event
* so, it means also replace a function by another
* filter the events by model, so a subscribed function will be triggered
  only if the event happens on a registered model

**********
Jobs Queue
**********

This section summarises the Job's Queue,
which articulates around several classes,
in broad terms,
:py:class:`~connector.queue.job.Job`
are executed by a
:py:class:`~connector.queue.worker.Worker`
which stores them in a
:py:class:`~connector.queue.queue.JobsQueue`.

Jobs are stored in the
:py:class:`~connector.queue.model.QueueJob` model.

Workers are stored in the
:py:class:`~connector.queue.model.QueueWorker` model.
A :py:class:`~connector.queue.worker.WorkerWatcher` create or destroy
new workers when new :py:class:`~openerp.modules.registry.Registry` are
created or destroyed, and signal the aliveness of the workers.

Jobs are assigned to a worker in the database by a cron.
The worker loads all the jobs assigned to itself in memory in the
:py:class:`~connector.queue.queue.JobsQueue`.
When a worker is dead, it is removed from the database,
so the jobs are freeed from the worker and can be assigned to another
one.

When multiple OpenERP processes are running,
a worker per process is running, but only those which are *CronWorkers*
enqueue and execute jobs, to avoid to clutter the HTTP processes.

A connectors developer is mostly interested by:

* Enqueue a job


*******
Backend
*******

A :py:class:`~connector.backend.Backend`
is a reference to an external system or service.

A backend is defined by a name and a version.
For instance `Magento 1.7`.

A reference can have a parent. The instance `Magento 1.7` is the child
of `Magento`.

:py:class:`~connector.connector.ConnectorUnit` classes are registered on
the backends. Then, we are able to ask a registered class to a backend.
If no class is found, it will search in its parent backend.

It is always accompanied by a concrete subclass of the model
:py:class:`~connector.backend_model.connector_backend`.

A connectors developer is mostly interested by:

* Declare the backends
* Register a ConnectorUnit on a backend
* Unregister a ConnectorUnit on a backend
* Get a connectorUnit from a backend


***********
Environment
***********

An :py:class:`~connector.connector.Environment`
is the scope from which we will do synchronizations.

It contains a :py:class:`~connector.backend.Backend`,
a record of a concrete subclass of the model
:py:class:`~connector.backend_model.connector_backend`,
a :py:class:`~connector.session.Session`
and the name of the model to work with.

A connectors developer is mostly interested by:

* Get a connectorUnit from an environment

*************
ConnectorUnit
*************

:py:class:`~connector.connector.ConnectorUnit`
are pluggable classes used for the synchronizations with the external
systems.

The connector defines some base classes, which you can find below.
Note that you can define your own ConnectorUnits as well without
reusing them.

Mappings
========

The base class is :py:class:`connector.unit.mapper.Mapper`.

A mapping translates an external record to an OpenERP record and
conversely.

It supports:

* direct mappings

    Fields *a* is written in field *b*.

* method mappings

    A method is used to convert one or many fields to one or many
    fields, with transformation.
    It can be filtered, for example only applied when the record is
    created or when the source fields are modified.

* submapping

    a sub-record (lines of a sale order) is converted using another
    Mapper

Synchronizers
=============

The base class is :py:class:`connector.unit.synchronizer.Synchronizer`.

A synchronizer defines the flow of a synchronization with a backend.
It can be a record's import or export, a deletion of something,
or anything else.
For instance, it will use the mappings
to convert the data between both systems,
the backend adapters to read or write data on the backend
and the binders to create the link between them.

Backend Adapters
================

The base class is
:py:class:`connector.unit.backend_adapter.BackendAdapter`.

An external adapter has a common interface to speak with the backend.
It translates the basic orders (search, read, write) to the protocol
used by the backend.

Binders
=======

The base class is
:py:class:`connector.connector.Binder`.

Binders are classes which know how to find the external ID for an
OpenERP ID, how to find the OpenERP ID for an external ID and how to
create the binding between them.

********
Bindings
********

The datamodel used in Magentoerpconnect_ (and other connectors) in
version 6.1 is invasive. They add their own fields on each synchronized
models (products, partners, ...). This not only is a mess on the views,
but also becomes limitating for the extensibility of the connectors. For
instance, actually the Magento `email` fields is stored on
`res.partner`. The fact is that a partner could be shared between 2
Magento's websites with different email. Product attributes may be
different per shop.

Another issue is the storage of the bindings between records in
`ir.model-data`. This model allows to store an external id, an openerp
id, a model and a a referential. This is a limitation when we need more
granularity in the bindings (`website_id` for a partner) or when there
is no external id but a couple of keys (product links).

The solution here is to properly stores the bindings on relation tables
between the referentials and the records `Figure 1`_. These relation tables will
also be able to store the additional data like the product attributes.

.. _`Figure 1`:
.. figure:: _static/09_datamodel.png
   :width: 50%
   :alt: New Datamodel for connectors V7.0
   :align: center

   Datamodel structure for connectors V7.0

******
Naming
******

We need to agree on a clear naming for the concepts exposed here and some
of the existing ones.

**********
Checkpoint
**********

.. _connector_ecommerce: https://launchpad.net/openerp-connector
