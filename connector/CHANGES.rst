Changelog
---------

3.0.0 (2015-04-01)
~~~~~~~~~~~~~~~~~~

/!\ Backwards incompatible changes inside.

* Add ``openerp.api.Environment`` in ``Session``
  It is accessible in ``self.env`` in ``Session`` and all
  ``ConnectorUnit`` instances.
  Also in ``ConnectorUnit``, ``model`` returns the current (new api!) model:

  .. code-block:: python

      # On the current model
      self.model.search([])
      self.model.browse(ids)
      # on another model
      self.env['res.users'].search([])
      self.env['res.users'].browse(ids)

* Deprecate the CRUD methods in ``Session``

  .. code-block:: python

      # NO
      self.session.search('res.partner', [])
      self.session.browse('res.partner', ids)

      # YES
      self.env['res.partner'].search([])
      self.env['res.partner'].browse(ids)

* ``Environment.set_lang()`` is removed. It was modifying the context
  in place which is not possible with the new frozendict context. It
  should be done with:

  .. code-block:: python

      with self.session.change_context(lang=lang_code):
          ...

* Add an argument on the Binders methods to return a browse record

  .. code-block:: python

      binder.to_openerp(magento_id, browse=True)

* Shorten ``ConnectorUnit.get_binder_for_model`` to
  ``ConnectorUnit.binder_for``
* Shorten ``ConnectorUnit.get_connector_unit_for_model`` to
  ``ConnectorUnit.unit_for``
* Renamed ``Environment`` to ``ConnectorEnvironment`` to avoid
  confusion with ``openerp.api.Environment``
* Renamed the class attribute ``ConnectorUnit.model_name`` to
  ``ConnectorUnit.for_model_name``.
* Added ``_base_binder``, ``_base_mapper``, ``_base_backend_adapter`` in
  the synchronizers (Importer, Exporter) so it is no longer required to
  override the ``binder``, ``mapper``, ``backend_adapter`` property
  methods
* ``Session.change_context()`` now supports the same
  argument/keyword arguments semantics than
  ``openerp.model.BaseModel.with_context()``.
* Renamed ``ExportSynchronizer`` to ``Exporter``
* Renamed ``ImportSynchronizer`` to ``Importer``
* Renamed ``DeleteSynchronizer`` to ``Deleter``
* ``Session.commit`` do not commit when tests are running
* Cleaned the methods that have been deprecated in version 2.x


2.2.0 (2014-05-26)
~~~~~~~~~~~~~~~~~~

* Pass a new parameter to listeners of 'on_recrod_create' ( vals:  field values of the new record, e.g {'field_name': field_value, ...})
* Replace the list of updated fields passed to listeners of 'on_record_write' by a dictionary of updated field values e.g {'field_name': field_value, ...}

2.1.1 (2014-02-06)
~~~~~~~~~~~~~~~~~~

* A user can be blocked because he has no access to the model queue.job when a
  job has been delayed. The creation of a job is low level and should not be
  restrained by the accesses of the user. (lp:1276182)

2.1.0 (2014-01-15 - warning: breaks compatibility)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* Add a new optional keyword argument 'description' to the delay() function of a
  job.  If given, the description is used as name of the queue.job record stored
  in OpenERP and displayed in the list of jobs.
* Fix: assignment of jobs to workers respect the priority of the jobs (lp:1252681)
* Pass a new parameter to listeners of 'on_record_create' ( vals:  field values
  of the new record, e.g {'field_name': field_value, ...})
* Replace the list of updated fields passed to listeners of 'on_record_write'
  by a dictionary of updated field values e.g {'field_name': field_value, ...}
* Add the possibility to use 'Modifiers' functions in the 'direct
  mappings' (details in the documentation of the Mapper class)
* Add a new optional keyword argument 'description' to the delay function of a job. If given, the description is used as name of the queue.job model stored in OpenErp
and displayed in the list of jobs.

2.0.1 (2013-09-12)
~~~~~~~~~~~~~~~~~~

* Developers of addons do no longer need to create an AbstractModel with a _name 'name_of_the_module.installed',
  instead, they just have to call connector.connector.install_in_connector() lp:1196859
* Added a script `openerp-connector-worker` to start processes for Jobs Workers when running OpenERP is multiprocessing
* Fix: inheritance broken when an orm.Model inherit from an or.AbstractModel. One effect was that the mail.thread features were no longer working (lp:1233355)


2.0.0
~~~~~

* First release


..
  Model:
  2.0.1 (date of release)
  ~~~~~~~~~~~~~~~~~~~~~~~

  * change 1
  * change 2
