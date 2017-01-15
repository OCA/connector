# -*- coding: utf-8 -*-
# Copyright 2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)


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
                mapper = self.components(name='magento.sale.importer.mapper')
                extra_mappers = self.components(
                    usage='magento.sale.importer.mapper',
                    multi=True,
                )
                # ...

        # use it:

        backend = self.env['magento.backend'].browse(1)
        work = backend.work_on('magento.sale.order')
        importer = work.components(name='magento.sale.importer')
        importer.run(1)


    """
    _name = 'collection.base'
    _description = 'Base Abstract Collection'

    @api.multi
    def work_on(self, model_name, **kwargs):
        return WorkContext(self, model_name, **kwargs)
