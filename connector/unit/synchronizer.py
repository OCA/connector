# -*- coding: utf-8 -*-
# Copyright 2013-2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from ..connector import ConnectorUnit
from .mapper import Mapper, ImportMapper, ExportMapper
from .backend_adapter import BackendAdapter


class Synchronizer(ConnectorUnit):
    """ Base class for synchronizers """

    # implement in sub-classes
    _model_name = None

    _base_mapper = Mapper
    _base_backend_adapter = BackendAdapter

    def __init__(self, connector_env):
        super(Synchronizer, self).__init__(connector_env)
        self._backend_adapter = None
        self._binder = None
        self._mapper = None

    def run(self):
        """ Run the synchronization """
        raise NotImplementedError

    @property
    def mapper(self):
        """ Return an instance of ``Mapper`` for the synchronization.

        The instanciation is delayed because some synchronisations do
        not need such an unit and the unit may not exist.

        :rtype: :py:class:`connector.unit.mapper.Mapper`
        """
        if self._mapper is None:
            self._mapper = self.unit_for(self._base_mapper)
        return self._mapper

    @property
    def binder(self):
        """ Return an instance of ``Binder`` for the synchronization.

        The instanciation is delayed because some synchronisations do
        not need such an unit and the unit may not exist.

        :rtype: :py:class:`connector.unit.binder.Binder`
        """
        if self._binder is None:
            self._binder = self.binder_for()
        return self._binder

    @property
    def backend_adapter(self):
        """ Return an instance of ``BackendAdapter`` for the
        synchronization.

        The instanciation is delayed because some synchronisations do
        not need such an unit and the unit may not exist.

        :rtype: :py:class:`connector.unit.backend_adapter.BackendAdapter`
        """
        if self._backend_adapter is None:
            self._backend_adapter = self.unit_for(self._base_backend_adapter)
        return self._backend_adapter


class Exporter(Synchronizer):
    """ Synchronizer for exporting data from Odoo to a backend """

    _base_mapper = ExportMapper


class Importer(Synchronizer):
    """ Synchronizer for importing data from a backend to Odoo """

    _base_mapper = ImportMapper


class Deleter(Synchronizer):
    """ Synchronizer for deleting a record on the backend """
