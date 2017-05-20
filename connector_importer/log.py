# -*- coding: utf-8 -*-
# Author: Simone Orsi
# Copyright 2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import os
import logging
from logging.handlers import RotatingFileHandler

logger = logging.getLogger('[importer]')
logger.setLevel(logging.INFO)

if os.environ.get('IMPORTER_LOG_PATH'):
    # use separated log file when developing
    FNAME = 'importer.log'

    base_path = os.environ.get('IMPORTER_LOG_PATH')
    if not os.path.exists(base_path):
        os.makedirs(base_path)

    # add a rotating handler
    handler = RotatingFileHandler(base_path + '/' + FNAME,
                                  maxBytes=1024 * 5,
                                  backupCount=5)
    logger.addHandler(handler)
    logging.info('logging to {}'.format(base_path + '/' + FNAME))
