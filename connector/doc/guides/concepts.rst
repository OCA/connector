.. _concepts:

##################
Connector Concepts
##################

The framework to develop connectors is decoupled in small pieces of
codes interacting together. Each of them can be used or not in an
implementation.

An example of implementation is the `OpenERP Magento Connector`_.

This document describes them from a high-level point of view and gives
pointers to more concrete 'how-to' or small tutorials.

.. _`OpenERP Magento Connector`: http://www.odoo-magento-connector.com

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

* register a new function on an event (see :py:class:`connector.event.Event`)
* unregister a function from an event (see :py:meth:`connector.event.Event.unsubscribe`)
* replace a consumer function by another one (see :py:class:`connector.event.Event`)
* filter the events by model, so a subscribed function will be triggered
  only if the event happens on a registered model

.. _jobs-queue:

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

* Delay a job (see the decorator :py:func:`~connector.queue.job.job`)


*******
Session
*******

A :py:class:`~connector.session.ConnectorSession` is a container for the usual
`cr`, `uid`, `context` used in OpenERP.
We use them accross the connectors.

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

* Declare the backends (see :py:class:`connector.backend.Backend`)
* Register a ConnectorUnit on a backend (see :py:class:`connector.backend.Backend`)
* Replace a ConnectorUnit on a backend (see :py:class:`connector.backend.Backend`)
* Use a different ConnectorUnit for a different version of a backend (see :py:class:`connector.backend.Backend`)


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

* Get a connectorUnit from an environment (:py:meth:`connector.connector.ConnectorUnit.get_connector_unit_for_model`,
  :py:meth:`connector.connector.ConnectorUnit.get_binder_for_model`)

*************
ConnectorUnit
*************

:py:class:`~connector.connector.ConnectorUnit`
are pluggable classes used for the synchronizations with the external
systems.

The connector defines some base classes, which you can find below.
Note that you can define your own ConnectorUnits as well.

Mappings
========

The base class is :py:class:`connector.unit.mapper.Mapper`.

A mapping translates an external record to an OpenERP record and
conversely.

It supports:

direct mappings
    Fields *a* is written in field *b*.

method mappings
    A method is used to convert one or many fields to one or many
    fields, with transformation.
    It can be filtered, for example only applied when the record is
    created or when the source fields are modified.

submapping
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


.. _binding:

********
Bindings
********

Here a binding means the link of a record between OpenERP and a backend.

The proposed implementation for the connectors widely use the
`_inherits` capabilities.

Say we import a customer from *Magento*.

We create a `magento.res.partner` model, which `_inherits`
`res.partner`.

This model, called a *binding* model, knows the ID of the partner in
OpenERP, the ID in Magento and the relation to the backend model.

It also stores all the necessary metadata related to this customer
coming from Magento.

.. _checkpoint:

**********
Checkpoint
**********

A checkpoint is a record in the model `connector.checkpoint` linked to a
model and a record, the connectors can create a new one when the user
needs to review imported documents.


.. _connector_ecommerce: https://github.com/OCA/connector-ecommerce
