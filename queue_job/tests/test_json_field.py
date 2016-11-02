# -*- coding: utf-8 -*-
# copyright 2016 Camptocamp
# license agpl-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import json

from odoo.tests import common
from odoo.addons.queue_job.fields import JobEncoder, JobDecoder


class TestJson(common.TransactionCase):

    def test_encoder(self):
        value = ['a', 1, self.env.ref('base.user_root')]
        value_json = json.dumps(value, cls=JobEncoder)
        expected = ('["a", 1, {"_type": "odoo_recordset", '
                    '"model": "res.users", "ids": [1]}]')
        self.assertEqual(value_json, expected)

    def test_decoder(self):
        value_json = ('["a", 1, {"_type": "odoo_recordset",'
                      '"model": "res.users", "ids": [1]}]')
        expected = ['a', 1, self.env.ref('base.user_root')]
        value = json.loads(value_json, cls=JobDecoder, env=self.env)
        self.assertEqual(value, expected)
