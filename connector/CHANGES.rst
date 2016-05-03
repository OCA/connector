Changelog
---------

Future
~~~~~~

* Add a retry pattern for jobs (https://github.com/OCA/connector/pull/75)

7.0.2.3.0 (2016-02-29)
~~~~~~~~~~~~~~~~~~~~~~

* Backport of jobrunner (https://github.com/OCA/connector/pull/53)
* Filter out databases with --db-filter (https://github.com/OCA/connector/pull/39)
* Perf. improvement: Call 'only_create' mapping functions only when the mapper is called with for_create=True (https://github.com/OCA/connector/pull/25)
* Activate transifex for translations (https://github.com/OCA/connector/pull/90)
* Security: Prevent to unpickle globals which are not jobs or whitelisted types (https://github.com/OCA/connector/pull/171)
* Fix: Option --load=web,connector no longer required (only for v7) (https://github.com/OCA/connector/pull/84)
* Fix: Add an index on queue_job.worker_id  (https://github.com/OCA/connector/pull/88)
* Fix: correct retry of jobs in jobrunner  (https://github.com/OCA/connector/pull/86)
* Fix: wrong name of field extracted from a mapping's closure (https://github.com/OCA/connector/pull/26)
* Fix: error 'AssertionError: 0 worker found in database instead of 1' (https://github.com/OCA/connector/pull/24)
* Fix: Allow the number of records being deleted to be limited to prevent timeouts or oom (https://github.com/OCA/connector/pull/158)


2.2.0 (2014-05-26)
~~~~~~~~~~~~~~~~~~

* Job arguments can now contain unicode strings (thanks to Stéphane Bidoul) lp:1288187
* List view of the jobs improved
* Jobs now support multicompany (thanks to Laurent Mignon) https://lists.launchpad.net/openerp-connector-community/msg00253.html)
* An action can be assigned to a job.  The action is called with a button on the job and could be something like open a form view or an url.

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
* When a job a delayed, the job's UUID is returned by the delay() function
* Refactoring of mappers. Much details here:
  https://code.launchpad.net/~openerp-connector-core-editors/openerp-connector/7.0-connector-mapper-refactor/+merge/194485

2.0.1 (2013-09-12)
~~~~~~~~~~~~~~~~~~

* Developers of addons do no longer need to create an AbstractModel with a _name 'name_of_the_module.installed',
  instead, they just have to call connector.connector.install_in_connector() lp:1196859
* Added a script `openerp-connector-worker` to start processes for Jobs Workers when running OpenERP is multiprocessing
* Fix: inheritance broken when an orm.Model inherit from an or.AbstractModel. One effect was that the mail.thread features were no longer working (lp:1233355)
* Fix: do no fail to start when OpenERP has access to a not-OpenERP database (lp:1233388)


2.0.0
~~~~~

* First release


..
  Model:
  2.0.1 (date of release)
  ~~~~~~~~~~~~~~~~~~~~~~~

  * change 1
  * change 2
