#!/usr/bin/env python
# -*- coding: utf-8 -*-
##############################################################################
#
#     This file is part of connector, an Odoo module.
#
#     Author: Stéphane Bidoul <stephane.bidoul@acsone.eu>
#     Copyright (c) 2015 ACSONE SA/NV (<http://acsone.eu>)
#
#     connector is free software: you can redistribute it and/or
#     modify it under the terms of the GNU Affero General Public License
#     as published by the Free Software Foundation, either version 3 of
#     the License, or (at your option) any later version.
#
#     connector is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU Affero General Public License for more details.
#
#     You should have received a copy of the
#     GNU Affero General Public License
#     along with connector.
#     If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
"""
Odoo Connector jobs runner
==========================

What's this?
------------
This is an alternative to connector workers, with the goal
of resolving issues due to the polling nature of workers:
* jobs do not start immediately even if there is a free worker
* workers may starve while other workers have too many jobs enqueued

It is fully compatible with the connector mechanism and only
replaces workers.

How?
----
* It starts as a thread in the Odoo main process
* It receives postgres NOTIFY messages each time jobs are
  added or updated in the queue_job table.
* It does not run jobs itself, but asks Odoo to run them through an
  anonymous /runjob HTTP request [1].

How to use
----------
* start Odoo with --load=web,connector
* disable "Enqueue Jobs" cron
* do NOT start openerp-connector-worker
* create jobs (eg using base_import_async) and observe they
  start immediately and in parallel

TODO
----
* See in the code below.

Notes
-----
[1] From a security standpoint, it is safe to have an anonymous HTTP
    request because this request only accepts to run jobs that are
    enqueued.
"""

from contextlib import closing
import logging
import select
import threading
import time

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import requests

from openerp import sql_db

from .channels import ChannelManager, STATE_ENQUEUED, STATES_NOT_DONE

# TODO: This is currently working nicely but for only
#       one database.

# TODO: since STATE_ENQUEUED is now very short lived state
#       we can automatically requeue (set pending) all
#       jobs that are enqueued since more than a few seconds
#       this is important as jobs will be stuck in that
#       state if this odoo-connector-runner runs while odoo does not

# TODO: should we try to recover from lost postgres connections?

# TODO: make all this configurable
_TMP_DATABASE = "jobrunner-1-v80"

SELECT_TIMEOUT = 60

_logger = logging.getLogger(__name__)


def _async_http_get(url):
    # TODO: better way to HTTP GET asynchronously (grequest, ...)?
    #       if this was python3 I would be doing this with
    #       asyncio, aiohttp and aiopg
    def urlopen():
        try:
            _logger.debug("GET %s", url)
            # we are not interested in the result, so we set a short timeout
            # but not too short so we log errors when Odoo
            # is not running at all
            requests.get(url, timeout=1)
        except requests.Timeout:
            pass
        except:
            _logger.exception("exception in GET %s", url)
    thread = threading.Thread(target=urlopen)
    thread.daemon = True
    thread.start()


class OdooConnectorRunner:

    def __init__(self, port=8069, channel_config_string='root:4'):
        self.port = port
        self.channel_manager = ChannelManager()
        self.channel_manager.simple_configure(channel_config_string)
        self.conn = psycopg2.connect(sql_db.dsn(_TMP_DATABASE)[1])
        self.conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        with closing(self.conn.cursor()) as cr:
            # this is the trigger that sends notifications when jobs change
            # TODO: perhaps we don't need to trigger ON DELETE?
            cr.execute("""
                DROP TRIGGER IF EXISTS queue_job_notify ON queue_job;

                CREATE OR REPLACE
                    FUNCTION queue_job_notify() RETURNS trigger AS $$
                DECLARE
                    uuid TEXT;
                BEGIN
                    IF TG_OP = 'DELETE' THEN
                        uuid = OLD.uuid;
                    ELSE
                        uuid = NEW.uuid;
                    END IF;
                    PERFORM pg_notify('connector',
                                      current_database() || ',' || uuid);
                    RETURN NULL;
                END;
                $$ LANGUAGE plpgsql;

                CREATE TRIGGER queue_job_notify
                    AFTER INSERT OR UPDATE OR DELETE
                    ON queue_job
                    FOR EACH ROW EXECUTE PROCEDURE queue_job_notify();
            """)
            cr.execute("LISTEN connector")
        self.notify_jobs(_TMP_DATABASE)

    def notify_jobs(self, db_name):
        # TODO: remove all jobs for database, in case we are reconnecting
        _logger.debug("loading all jobs")
        with closing(self.conn.cursor()) as cr:
            # TODO: channel_name
            # TODO: sequence
            cr.execute("SELECT NULL, uuid, 0, date_created, priority, eta, state " \
                       "  FROM queue_job WHERE state in %s", (STATES_NOT_DONE,))
            for channel_name, uuid, seq, date_created, priority, eta, state in cr.fetchall():
                self.channel_manager.notify(db_name, channel_name, uuid,
                                            seq, date_created, priority, eta, state)
        _logger.debug("loaded all jobs")

    def notify_job(self, db_name, uuid):
        with closing(self.conn.cursor()) as cr:
            # TODO: channel_name
            # TODO: sequence
            cr.execute("SELECT NULL, uuid, 0, date_created, priority, eta, state " \
                       "  FROM queue_job WHERE uuid = %s", (uuid,))
            res = cr.fetchall()
            if res:
                for channel_name, uuid, seq, date_created, priority, eta, state in res:
                    self.channel_manager.notify(db_name, channel_name, uuid,
                                                seq, date_created, priority, eta, state)
            else:
                # job not found: remove it
                _logger.warning("job %s not found in database", uuid)
                self.channel_manager.notify(db_name, None, uuid,
                                            None, None, None, None, None)

    def run_jobs(self):
        for job in self.channel_manager.get_jobs_to_run():
            _logger.info("asking Odoo to run job %s on db %s",
                         job.uuid, job.db_name)
            with closing(self.conn.cursor()) as cr:
                cr.execute("UPDATE queue_job "
                           "   SET state=%s, "
                           "       date_enqueued=NOW() "
                           "WHERE uuid=%s",
                           (STATE_ENQUEUED, job.uuid))
            _async_http_get('http://localhost:%d'
                            '/runjob?db=%s&job_uuid=%s' %
                            (self.port, job.db_name, job.uuid,))

    def process_notifications(self):
        while self.conn.notifies:
            notification = self.conn.notifies.pop()
            db_name, uuid = notification.payload.split(',')
            self.notify_job(db_name, uuid)

    def wait_notification(self):
        if self.conn.notifies:
            return
        # wait for something to happen in the queue_job table
        conns, _, _ = select.select([self.conn], [], [], SELECT_TIMEOUT)
        if conns:
            for conn in conns:
                conn.poll()
        else:
            _logger.debug("select timeout")

    def run_forever(self):
        _logger.info("starting")
        while True:
            try:
                self.process_notifications()
                self.run_jobs()
                self.wait_notification()
            except KeyboardInterrupt:
                _logger.info("stopping")
                break
            except:
                _logger.exception("exception, sleeping a bit and continuing")
                time.sleep(1)
