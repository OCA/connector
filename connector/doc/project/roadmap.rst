.. _roadmap:

#######
Roadmap
#######

This document lists the feature that we want to develop for the
connector. They are not sorted by priority. Any contribution on theses
points will be welcome.

* Queue: use PostgreSQL `notify` for direct enqueue of jobs

    It seems to work but stays one problem:

    we should identify the HTTP workers and Cron workers to activate the
    listener only on the latters. I didn't find a way to do that and I
    don't think we can monkey patch the workers as they are started
    before the loading of the addons.

    https://code.launchpad.net/~magentoerpconnect-core-editors/magentoerpconnect/7.0-prototype-multi-worker-notify/+merge/147387

* Add facilities to parse the errors from the jobs so we can replace it
  by more contextual and helpful errors.
