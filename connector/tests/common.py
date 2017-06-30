# -*- coding: utf-8 -*-
# Copyright 2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo.addons.component.tests.common import (
    TransactionComponentRegistryCase,
)


class ConnectorTransactionCase(TransactionComponentRegistryCase):
    """ Can be used as base class to test connectors

    It's based on an Odoo TransactionCase, so it include an Odoo ``env``.
    Alongside, it creates a Component Registry in ``self.comp_registry``,
    in which it preloads all the Connector base components.

    You can then load the components you want to test in your tests and
    load stub components::


        from odoo.addons.connector_magento.models.product.importer import (
            CatalogImageImporter
        )

        class TestImportProductImage(MagentoSyncTestCase):

            def test_import_images(self):

                # create a Stub component replacing the normal adapter
                # (it has the same '_usage')
                class StubProductAdapter(Component):

                    _name = 'stub.product.adapter'
                    _collection = 'magento.backend'
                    _usage = 'backend.adapter'
                    _apply_on = 'magento.product.product'

                    def get_images(self, id, storeview_id=None):
                        return [...]

                # build the Stub and the component we want to test
                self._build_components(StubProductAdapter,
                                       CatalogImageImporter)

                work = WorkContext(model_name='magento.product.product',
                                   collection=self.backend,
                                   components_registry=self.comp_registry)
                image_importer = work.component_by_name(
                    'magento.product.image.importer'
                )
                # the image importer will lookup the 'backend.adapter'
                # component, which will our Stub, and call get_images()
                image_importer.run(111)
                # ... asserts below

    """
