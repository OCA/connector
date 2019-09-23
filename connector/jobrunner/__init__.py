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

import logging
import os
from threading import Thread
import time

from openerp.service import server
from openerp.tools import config

from .runner import ConnectorRunner, _channels

_logger = logging.getLogger(__name__)

START_DELAY = 5


# Here we monkey patch the Odoo server to start the job runner thread
# in the main server process (and not in forked workers). This is
# very easy to deploy as we don't need another startup script.


class ConnectorRunnerThread(Thread):

    def __init__(self):
        Thread.__init__(self)
        self.daemon = True
        port = os.environ.get('ODOO_CONNECTOR_PORT') or config['xmlrpc_port']
        channels = _channels()
        self.runner = ConnectorRunner(port or 8069, channels or 'root:1')

    def run(self):
        # sleep a bit to let the workers start at ease
        time.sleep(START_DELAY)
        self.runner.run()

    def stop(self):
        self.runner.stop()


class WorkerJobRunner(server.Worker):
    """ Jobrunner workers """

    def __init__(self, multi):
        super(WorkerJobRunner, self).__init__(multi)
        self.watchdog_timeout = None
        port = os.environ.get('ODOO_CONNECTOR_PORT') or config['xmlrpc_port']
        channels = _channels()
        self.runner = ConnectorRunner(port, channels or 'root:1')

    def sleep(self):
        pass

    def signal_handler(self, sig, frame):
        _logger.debug("WorkerJobRunner (%s) received signal %s", self.pid, sig)
        super(WorkerJobRunner, self).signal_handler(sig, frame)
        self.runner.stop()

    def process_work(self):
        _logger.debug("WorkerJobRunner (%s) starting up", self.pid)
        time.sleep(START_DELAY)
        self.runner.run()


runner_thread = None

orig_prefork__init__ = server.PreforkServer.__init__
orig_prefork_process_spawn = server.PreforkServer.process_spawn
orig_prefork_worker_pop = server.PreforkServer.worker_pop
orig_threaded_start = server.ThreadedServer.start
orig_threaded_stop = server.ThreadedServer.stop


def prefork__init__(server, app):
    res = orig_prefork__init__(server, app)
    server.jobrunner = {}
    return res


def prefork_process_spawn(server):
    orig_prefork_process_spawn(server)
    if _channels() and not server.jobrunner:
        server.worker_spawn(WorkerJobRunner, server.jobrunner)


def prefork_worker_pop(server, pid):
    res = orig_prefork_worker_pop(server, pid)
    if pid in server.jobrunner:
        server.jobrunner.pop(pid)
    return res


def threaded_start(server, *args, **kwargs):
    global runner_thread
    res = orig_threaded_start(server, *args, **kwargs)
    if _channels() and not config['stop_after_init']:
        _logger.info("starting jobrunner thread (in threaded server)")
        runner_thread = ConnectorRunnerThread()
        runner_thread.start()
    return res


def threaded_stop(server):
    global runner_thread
    if runner_thread:
        runner_thread.stop()
    res = orig_threaded_stop(server)
    if runner_thread:
        runner_thread.join()
        runner_thread = None
    return res


server.PreforkServer.__init__ = prefork__init__
server.PreforkServer.process_spawn = prefork_process_spawn
server.PreforkServer.worker_pop = prefork_worker_pop
server.ThreadedServer.start = threaded_start
server.ThreadedServer.stop = threaded_stop
