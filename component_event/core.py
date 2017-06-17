# -*- coding: utf-8 -*-
# Copyright 2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)


from odoo.addons.component.core import WorkContext


class EventWorkContext(WorkContext):
    """ TODO

    """

    def __init__(self, model_name=None, collection=None, env=None,
                 from_recordset=None,
                 components_registry=None, **kwargs):
        if not (collection or env):
            raise ValueError('collection or env is required')
        if collection and env:
            # when a collection is used, the env will be the one of
            # the collection
            raise ValueError('collection and env cannot both be provided')

        self.env = env
        super(EventWorkContext, self).__init__(
            model_name=model_name, collection=collection,
            components_registry=components_registry,
            from_recordset=from_recordset,
            **kwargs
        )
        if self._env:
            self._propagate_kwargs.remove('collection')
            self._propagate_kwargs.append('env')

    @property
    def env(self):
        """ Return the current Odoo env """
        if self._env:
            return self._env
        return super(EventWorkContext, self).env

    @env.setter
    def env(self, value):
        self._env = value

    @property
    def collection(self):
        """ Return the current Odoo env """
        if self._collection:
            return self._collection
        raise ValueError('No collection, it is optional for EventWorkContext')

    @collection.setter
    def collection(self, value):
        self._collection = value

    def __str__(self):
        return ("EventWorkContext(%s,%s)" %
                (repr(self._env or self._collection), self.model_name))
