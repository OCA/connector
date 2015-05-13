.. _jobrunner:


#######################################
Configuring channels and the job runner
#######################################

.. automodule:: connector.jobrunner.runner

What is a channel?
------------------

.. autoclass:: connector.jobrunner.channels.Channel

How to configure Channels?
--------------------------

The ``ODOO_CONNECTOR_CHANNELS`` environment variable must be
set before starting Odoo in order to enable the job runner
and configure the capacity of the channels.

The general syntax is ``channel(.subchannel)*(:capacity(:key(=value)?)*)?,...``.

Intermediate subchannels which are not configured explicitly are autocreated
with an unlimited capacity (except the root channel which if not configured gets
a default capacity of 1).

Example ``ODOO_CONNECTOR_CHANNELS``:

* ``root:4``: allow up to 4 concurrent jobs in the root channel.
* ``root:4,root.sub:2``: allow up to 4 concurrent jobs in the root channel and
  up to 2 concurrent jobs in the channel named ``root.sub``.
* ``sub:2``: the same.
