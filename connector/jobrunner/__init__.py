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

from openerp.tools import config

from .runner import ConnectorRunner

_logger = logging.getLogger(__name__)

START_DELAY = 5


enable = os.environ.get('ODOO_CONNECTOR_CHANNELS')


def run():
    # sleep a bit to let the workers start at ease
    time.sleep(START_DELAY)
    port = os.environ.get('ODOO_CONNECTOR_PORT') or config['xmlrpc_port']
    channels = os.environ.get('ODOO_CONNECTOR_CHANNELS')
    runner = ConnectorRunner(port or 8069, channels or 'root:1')
    runner.run_forever()
