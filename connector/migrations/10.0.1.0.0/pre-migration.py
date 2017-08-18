# -*- coding: utf-8 -*-
# Copyright 2017 Tecnativa - Vicent Cubells
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).


def migrate(cr, version):
    if not version:
        return
    # Delete noupdate data
    cr.execute("""
        DELETE FROM ir_model_data
        WHERE name = 'queue_job_comp_rule'
    """)
