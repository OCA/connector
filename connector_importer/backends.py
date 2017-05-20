# -*- coding: utf-8 -*-
# Author: Simone Orsi
# Copyright 2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import openerp.addons.connector.backend as backend


import_backend = backend.Backend('import_backend')
""" Generic Import Backend """

import_backend_default = backend.Backend(parent=import_backend, version='1.0')
""" Import backend for version 1.0 """
