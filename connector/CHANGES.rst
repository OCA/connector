Changelog
---------

2.0.1.dev0
~~~~~~~~~~

* Pass a new parameter to listeners of  'on_recrod_write' ( vals:  field values of the new record, e.g {'field_name': field_value, ...})
* Replace the list of updated fields passed to listeners of 'on_record_write' by a dictionary of updated field values e.g {'field_name': field_value, ...}  

2.0.1 (2013-09-12)
~~~~~~~~~~~~~~~~~~

* Developers of addons do no longer need to create an AbstractModel with a _name 'name_of_the_module.installed',
  instead, they just have to call connector.connector.install_in_connector() lp:1196859
* Added a script `openerp-connector-worker` to start processes for Jobs Workers when running OpenERP is multiprocessing


2.0.0
~~~~~

* First release


..
  Model:
  2.0.1 (date of release)
  ~~~~~~~~~~~~~~~~~~~~~~~

  * change 1
  * change 2
