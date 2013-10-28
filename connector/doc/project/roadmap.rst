.. _roadmap:

#######
Roadmap
#######

Here is a list of things we may agree to merge.

* Queue: use PostgreSQL `notify` for direct enqueue of jobs

  Prototype on https://code.launchpad.net/~magentoerpconnect-core-editors/magentoerpconnect/7.0-prototype-multi-worker-notify/+merge/147387

* Add facilities to parse the errors from the jobs so we can replace it
  by more contextual and helpful errors.

* A logger which keeps in a buffer all the logs and flushes them when an error
  occurs in a synchronization, clears them if it succeeded

Please also have a look on the registered blueprints on https://blueprints.launchpad.net/openerp-connector
