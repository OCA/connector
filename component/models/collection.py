# -*- coding: utf-8 -*-
# Copyright 2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

"""

Collection Model
================

This is the base Model shared by all the Collections.
In the context of the Connector, a collection is the Backend.
The `_name` given to the Collection Model will be the name
to use in the `_collection` of the Components usable for the Backend.

"""


from odoo import models, api
from ..core import WorkContext


class Collection(models.AbstractModel):
    """ The model on which components are subscribed

    It would be for instance the ``backend`` for the connectors.

    Example::

        class MagentoBackend(models.Model):
            _name = 'magento.backend'  # name of the collection
            _inherit = 'collection.base'


        class MagentoSaleImporter(Component):
            _name = 'magento.sale.importer'
            _apply_on = 'magento.sale.order'
            _collection = 'magento.backend'  # name of the collection

            def run(self, magento_id):
                mapper = self.component(usage='import.mapper')
                extra_mappers = self.many_components(
                    usage='import.mapper.extra',
                )
                # ...

    Use it::

        >>> backend = self.env['magento.backend'].browse(1)
        >>> work = backend.work_on('magento.sale.order')
        >>> importer = work.component(usage='magento.sale.importer')
        >>> importer.run(1)

    See also: :class:`odoo.addons.component.core.WorkContext`


    """
    _name = 'collection.base'
    _description = 'Base Abstract Collection'

    @api.multi
    def work_on(self, model_name, **kwargs):
        """ Entry-point for the components

        Start a work using the components on the model.
        Any keyword argument will be assigned to the work context.
        See documentation of :class:`odoo.addons.component.core.WorkContext`.

        """
        self.ensure_one()
        return WorkContext(self, model_name, **kwargs)
