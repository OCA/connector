# -*- coding: utf-8 -*-
##############################################################################
#
#    Author: Guewen Baconnier
#    Copyright 2013 Camptocamp SA
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from ..connector import ConnectorUnit
from .mapper import Mapper, ImportMapper, ExportMapper
from .backend_adapter import BackendAdapter


class Synchronizer(ConnectorUnit):
    """ Base class for synchronizers """

    # implement in sub-classes
    _model_name = None

    def __init__(self, environment):
        super(Synchronizer, self).__init__(environment)
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
            self._mapper = self.environment.get_connector_unit(Mapper)
        return self._mapper

    @property
    def binder(self):
        """ Return an instance of ``Binder`` for the synchronization.

        The instanciation is delayed because some synchronisations do
        not need such an unit and the unit may not exist.

        :rtype: :py:class:`connector.unit.binder.Binder`
        """
        if self._binder is None:
            self._binder = self.get_binder_for_model()
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
            get_unit = self.environment.get_connector_unit
            self._backend_adapter = get_unit(BackendAdapter)
        return self._backend_adapter


class ExportSynchronizer(Synchronizer):
    """ Synchronizer for exporting data from OpenERP to a backend """

    @property
    def mapper(self):
        """ Return an instance of ``Mapper`` for the synchronization.

        The instanciation is delayed because some synchronisations do
        not need such an unit and the unit may not exist.

        :rtype: :py:class:`connector.unit.mapper.ExportMapper`
        """
        if self._mapper is None:
            self._mapper = self.environment.get_connector_unit(ExportMapper)
        return self._mapper


class ImportSynchronizer(Synchronizer):
    """ Synchronizer for importing data from a backend to OpenERP """

    @property
    def mapper(self):
        """ Return an instance of ``Mapper`` for the synchronization.

        The instanciation is delayed because some synchronisations do
        not need such an unit and the unit may not exist.

        :rtype: :py:class:`connector.unit.mapper.ImportMapper`
        """
        if self._mapper is None:
            self._mapper = self.environment.get_connector_unit(ImportMapper)
        return self._mapper


class DeleteSynchronizer(Synchronizer):
    """ Synchronizer for deleting a record on the backend """
