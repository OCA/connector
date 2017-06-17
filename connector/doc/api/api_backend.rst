Backend Models
==============

The components articulates around a collection, which in the context of the
connectors is called a Backend.

It must be defined as a Model.

Example with the Magento Connector:

.. code-block:: python

    # in magentoerpconnect/magento_model.py

    class MagentoBackend(models.Model):
        _name = 'magento.backend'
        _description = 'Magento Backend'
        _inherit = 'connector.backend'

        # the version in not mandatory
        @api.model
        def _select_versions(self):
            """ Available versions

            Can be inherited to add custom versions.
            """
            return [('1.7', 'Magento 1.7')]

        version = fields.Selection(
            selection='_select_versions',
            string='Version',
            required=True,
        )
        location = fields.Char(string='Location', required=True)
        username = fields.Char(string='Username')
        password = fields.Char(string='Password')

        # <snip>


.. automodule:: connector.backend_model
   :members:
   :undoc-members:
   :show-inheritance:
