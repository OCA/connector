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

from .runner import ConnectorRunner

_logger = logging.getLogger(__name__)

START_DELAY = 5


# Here we monkey patch the Odoo server to start the job runner thread
# in the main server process (and not in forked workers). This is
# very easy to deploy as we don't need another startup script.
# The drawback is that it is not possible to extend the Odoo
# server command line arguments, so we resort to environment variables
# to configure the runner (channels mostly).


# TODO: this is a temporary flag to enable the connector runner
enable = os.environ.get('ODOO_CONNECTOR_RUNNER_ENABLE')


def run():
    # sleep a bit to let the workers start at ease
    time.sleep(START_DELAY)
    port = os.environ.get('ODOO_CONNECTOR_PORT') or config['xmlrpc_port']
    channels = os.environ.get('ODOO_CONNECTOR_CHANNELS')
    runner = ConnectorRunner(port or 8069, channels or 'root:1')
    runner.run_forever()


orig_prefork_start = server.PreforkServer.start
orig_threaded_start = server.ThreadedServer.start
orig_gevent_start = server.GeventServer.start


def prefork_start(server, *args, **kwargs):
    res = orig_prefork_start(server, *args, **kwargs)
    if enable and not config['stop_after_init']:
        _logger.info("starting jobrunner thread (in prefork server)")
        thread = Thread(target=run)
        thread.daemon = True
        thread.start()
    return res


def threaded_start(server, *args, **kwargs):
    res = orig_threaded_start(server, *args, **kwargs)
    if enable and not config['stop_after_init']:
        _logger.info("starting jobrunner thread (in threaded server)")
        thread = Thread(target=run)
        thread.daemon = True
        thread.start()
    return res


def gevent_start(server, *args, **kwargs):
    res = orig_gevent_start(server, *args, **kwargs)
    if enable and not config['stop_after_init']:
        _logger.info("starting jobrunner thread (in gevent server)")
        # TODO: gevent spawn?
        raise RuntimeError("not implemented")
    return res


server.PreforkServer.start = prefork_start
server.ThreadedServer.start = threaded_start
server.GeventServer.start = gevent_start
