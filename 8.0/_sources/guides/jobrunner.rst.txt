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

Alternatively, set the channel configuration in the Odoo configuration file:

.. code-block:: cfg

    [options-connector]
    channels = root:4

If the channel configuration is present in both the environment variable and
the configuration file, the environment variable takes precedence.

The general syntax is ``channel(.subchannel)*(:capacity(:key(=value)?)*)?,...``.

Intermediate subchannels which are not configured explicitly are autocreated
with an unlimited capacity (except the root channel which if not configured gets
a default capacity of 1).

Example values for ``ODOO_CONNECTOR_CHANNELS`` or ``options-connector:channels``:

* ``root:4``: allow up to 4 concurrent jobs in the root channel.
* ``root:4,root.sub:2``: allow up to 4 concurrent jobs in the root channel and
  up to 2 concurrent jobs in the channel named ``root.sub``.
* ``sub:2``: the same.

It's also possible to separate channel entries with line breaks, which is more
readable in the configuration file:

.. code-block:: cfg

    [options-connector]
    channels =
        root:4
        sub:2
