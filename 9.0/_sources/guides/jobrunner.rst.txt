.. _jobrunner:


#######################################
Configuring the job runner and channels
#######################################

.. automodule:: connector.jobrunner.runner

What is a channel?
------------------

.. autoclass:: connector.jobrunner.channels.Channel

How to configure Channels?
--------------------------

The ``ODOO_CONNECTOR_CHANNELS`` environment variable can be
set before starting Odoo in order to adjust the capacity of the channels.

Alternatively, set the channels configuration in the Odoo configuration file:

.. code-block:: cfg

    [options-connector]
    channels = root:4

If neither of the above methods is used, the default configuration of ``root:1``
is adopted by default.

If the channel configuration is present in both the environment variable and
the configuration file, the environment variable takes precedence.

The general syntax is ``channel(.subchannel)*(:capacity(:key(=value)?)*)?,...``.

Intermediate subchannels which are not configured explicitly are autocreated
with an unlimited capacity (except the root channel which if not configured gets
a default capacity of 1).

A delay in seconds between jobs can be set at the channel level with
the ``throttle`` key.

Example values for ``ODOO_CONNECTOR_CHANNELS`` or ``options-connector:channels``:

* ``root:4``: allow up to 4 concurrent jobs in the root channel.
* ``root:4,root.sub:2``: allow up to 4 concurrent jobs in the root channel and
  up to 2 concurrent jobs in the channel named ``root.sub``.
* ``sub:2``: the same.
* ``root:4:throttle=2``: wait at least 2 seconds before starting the next job
