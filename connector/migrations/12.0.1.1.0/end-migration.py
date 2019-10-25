# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    """Now that everything has been loaded, compute the value of
    channel_method_name.
    """

    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {})
    checkpoints = env["connector.checkpoint"].search([])
    checkpoints._compute_company()
