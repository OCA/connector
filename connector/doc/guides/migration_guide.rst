.. _migration-guide:

#############################
Migration Guide to Components
#############################

During the year 2017, the connector evolved greatly.
Two majors parts have been rewritten:

* The Job Queue API
* The ``ConnectorUnit`` API, which is the core of the composability of the
  Connector. It has been replaced by a standalone addon called ``component``.

This guide will show how to migrate from the old API to the new one.

**************
Migrating Jobs
**************

Jobs are now more integrated within the Odoo API. They are no longer
standalone functions but are applied on methods of Models.  Another change is
that they have been extracted into their own addon, so obviously the Python
paths change.

Declaration of a job
====================

Before
------

.. code-block:: python

    from odoo.addons.connector.queue.job import job, related_action
    from ..related_action import unwrap_binding, link

    # function at module-level
    @job(default_channel='root.magento')
    @related_action(action=link)
    def import_record(session, model_name, backend_id, magento_id, force=False):
        """ Import a record from Magento """
        # ...

    @job(default_channel='root.magento')
    @related_action(action=unwrap_binding)
    def export_record(session, model_name, binding_id, fields=None):
        """ Import a record from Magento """
        # ...


After
-----

.. code-block:: python

    from odoo.addons.queue_job.job import job, related_action
    from odoo import api, models


    class MagentoBinding(models.AbstractModel):
        _name = 'magento.binding'
        _inherit = 'external.binding'
        _description = 'Magento Binding (abstract)'

        @job(default_channel='root.magento')
        @related_action(action='related_action_magento_link')
        @api.model
        def import_record(self, backend, external_id, force=False):
            """ Import a Magento record """
            backend.ensure_one()
            # ...

        @job(default_channel='root.magento')
        @related_action(action='related_action_unwrap_binding')
        @api.multi
        def export_record(self, fields=None):
            """ Export a record on Magento """
            self.ensure_one()
            # ...


Observations
------------

* The job is declared on the generic abstract binding model from which all
  bindings inherit. This is not a requirement, but for this kind of job it is
  the perfect fit.
* ``session``, ``model_name`` and ``binding_id`` are no longer required as they
  are already known in ``self``.  Jobs can be used as well on ``@api.multi`` and
  ``@api.model``.
* Passing arguments as records is supported, in the new version of
  ``import_record``, no need to browse on the backend if a record was passed
* The action of a related action is now the name of a method on the
  ``queue.job`` model.
* If you need to share a job between several models, put them in an
  AbstractModel and add an ``_inherit`` on the models.

Links
-----

* :meth:`odoo.addons.queue_job.job.job`
* :meth:`odoo.addons.queue_job.job.related_action`


Invocation of a job
===================

Before
------

.. code-block:: python

    from odoo.addons.connector.session import ConnectorSession
    from .unit.export_synchronizer import export_record


    class MyBinding(models.Model):
        _name = 'my.binding'
        _inherit = 'magento.binding'

        @api.multi
        def button_trigger_export_sync(self):
            session = ConnectorSession.from_env(self.env)
            export_record(session, binding._name, self.id, fields=['name'])

        @api.multi
        def button_trigger_export_async(self):
            session = ConnectorSession.from_env(self.env)
            export_record.delay(session, self._name, self.id,
                                fields=['name'], priority=12)


After
-----

.. code-block:: python

    class MyBinding(models.Model):
        _name = 'my.binding'

        @api.multi
        def button_trigger_export_sync(self):
            self.export_record(fields=['name'])

        @api.multi
        def button_trigger_export_async(self):
            self.with_delay(priority=12).export_record(fields=['name'])

Observations
------------

* No more imports are needed for the invocation
* ``ConnectorSession`` is now dead
* Arguments for the job (such as ``priority``) are no longer mixed with the
  arguments passed to the method
* When the job is called on a "browse" record, the job will be executed
  on an instance of this record:

  .. code-block:: python

      >>> binding = self.env['my.binding'].browse(1)
      >>> binding.button_trigger_export_async()

  In the execution of the job:

  .. code-block:: python

      @job
      def export_record(self, fields=None):
          print self
          print fields
      # =>
      # my.binding,1
      # ['name']

Links
-----

* :meth:`odoo.addons.queue_job.job.job`
* :meth:`odoo.addons.queue_job.models.base.Base.with_delay`

********************
Migrating Components
********************

* backend version: no longer a dispatch at class level; do at method level
* inheritance, all AbstractComponent, Component, _name, _inherit
* set _collection
* replace unit_for
* create a base component
* no hesitation to create a dedicated ``_usage`` such as ``'tracking.exporter``
