# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).


def migrate(cr, version):
    if not version:
        return
    cr.execute(
        """
        ALTER TABLE connector_checkpoint
        ADD COLUMN company_id integer
    """
    )
