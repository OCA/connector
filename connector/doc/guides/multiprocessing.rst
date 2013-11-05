.. _multiprocessing:


######################################
Use the connector with multiprocessing
######################################

When OpenERP is launched with 1 process, the jobs worker will run
threaded in the same process.

When OpenERP is launched with multiple processes using the option
``--workers``, the jobs workers are not independant processes, however,
you have to launch them separately with the script
``openerp-connector-worker`` located in the connector module.

It takes the same arguments and configuration file than the OpenERP
server.

.. important:: The Python path must contain the path to the OpenERP
               server when ``openerp-connector-worker`` is launched.

Example::

    $ PYTHONPATH=/path/to/server connector/openerp-connector-worker --config /path/to/configfile \
      --workers=2 --logfile=/path/to/logfile

The 'Enqueue Jobs' scheduled action is useless when multiprocessing is
used.

.. note:: The ``openerp-connector-worker`` should not be launched
          alongside OpenERP when the latter does not run in multiprocess
          mode, because the interprocess signaling would not be done.

.. hint:: The Magento Connector's buildout contains builtin commands to launch the workers:
          :ref:`connectormagento:installation-with-buildout`
