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
from .binder import Binder
from .mapper import Mapper
from .backend_adapter import BackendAdapter


class Synchronizer(ConnectorUnit):
    """ Base class for synchronizers """

    # implement in sub-classes
    _model_name = None

    def run(self):
        """ Run the synchronization """
        raise NotImplementedError


class ImportExportSynchronizer(Synchronizer):
    """ Common base class for import and exports """

    def __init__(self, reference, session):
        super(ImportExportSynchronizer, self).__init__(reference)
        self.session = session
        self.model = self.session.pool.get(self.model_name)

        self._binder = None
        self._external_adapter = None
        self._processor = None

    @property
    def binder(self):
        if self._binder is None:
            self._binder = self.reference.get_class(
                    Binder, self.model_name)(self.reference, self.session)
        return self._binder

    @binder.setter
    def binder(self, binder):
        self._binder = binder

    @property
    def backend_adapter(self):
        if self._backend_adapter is None:
            adapter_cls = self.reference.get_class(BackendAdapter,
                                                   self.model_name)
            self._backend_adapter = adapter_cls(self.reference, self.session)
        return self._external_adapter

    @backend_adapter.setter
    def backend_adapter(self, backend_adapter):
        self._backend_adapter = backend_adapter

    @property
    def mapper(self):
        if self._mapper is None:
            self._mapper = self.reference.get_class(
                    Mapper, self.model_name)(self.reference, self.session)
        return self._mapper

    @mapper.setter
    def mapper(self, mapper):
        self._mapper = mapper



class ExportSynchronizer(ImportExportSynchronizer):
    """ Synchronizer for exporting data from OpenERP to a backend """


class ImportSynchronizer(ImportExportSynchronizer):
    """ Synchronizer for importing data from a backend to OpenERP """
