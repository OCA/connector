# -*- coding: utf-8 -*-
# Copyright 2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from .core import Component
from .collection import collection_registry


class BaseComponent(Component):
    _name = 'base'

    # TODO: add __init__ with 'connector_env'


class Collection(Component):
    """ Find components in the Collection Registry """

    _name = 'collection'

    def find(self, name=None, purpose=None, model_name=None):
        # replace 'test.backend' by self.connector_env.backend_record._name
        collection_registry.find(
            'test.backend',
            name=name,
            purpose=purpose,
            model_name=model_name,
            multi=False,
        )

    def find_all(self, name=None, purpose=None, model_name=None):
        # replace 'test.backend' by self.connector_env.backend_record._name
        collection_registry.find(
            'test.backend',
            name=name,
            purpose=purpose,
            model_name=model_name,
            multi=True,
        )


class Mapper(Component):
    _name = 'mapper'
