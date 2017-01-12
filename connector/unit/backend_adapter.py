# -*- coding: utf-8 -*-
# Copyright 2013-2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from ..connector import ConnectorUnit


class BackendAdapter(ConnectorUnit):
    """ Base Backend Adapter for the connectors """

    _model_name = None  # define in sub-classes


class CRUDAdapter(BackendAdapter):
    """ Base External Adapter specialized in the handling
    of records on external systems.

    Subclasses can implement their own implementation for
    the methods.
    """

    _model_name = None

    def search(self, *args, **kwargs):
        """ Search records according to some criterias
        and returns a list of ids """
        raise NotImplementedError

    def read(self, *args, **kwargs):
        """ Returns the information of a record """
        raise NotImplementedError

    def search_read(self, *args, **kwargs):
        """ Search records according to some criterias
        and returns their information"""
        raise NotImplementedError

    def create(self, *args, **kwargs):
        """ Create a record on the external system """
        raise NotImplementedError

    def write(self, *args, **kwargs):
        """ Update records on the external system """
        raise NotImplementedError

    def delete(self, *args, **kwargs):
        """ Delete a record on the external system """
        raise NotImplementedError
