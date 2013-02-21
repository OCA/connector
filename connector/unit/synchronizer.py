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
from .mapper import Mapper, ImportMapper, ExportMapper
from .backend_adapter import BackendAdapter


class Synchronizer(ConnectorUnit):
    """ Base class for synchronizers """

    # implement in sub-classes
    _model_name = None

    def __init__(self, environment):
        super(Synchronizer, self).__init__(environment)
        model_name = environment.model_name
        get_class = self.backend.get_class
        self.binder = get_class(Binder, model_name)(environment)
        self.backend_adapter = get_class(BackendAdapter, model_name)(environment)
        self.mapper = None
        self._init_mapper(environment)

    def _init_mapper(self, environment):
        model_name = environment.model_name
        get_class = self.backend.get_class
        self.mapper = get_class(Mapper, model_name)(environment)

    def run(self):
        """ Run the synchronization """
        raise NotImplementedError


class ExportSynchronizer(Synchronizer):
    """ Synchronizer for exporting data from OpenERP to a backend """

    def _init_mapper(self, environment):
        model_name = environment.model_name
        get_class = self.backend.get_class
        self.mapper = get_class(ExportMapper, model_name)(environment)


class ImportSynchronizer(Synchronizer):
    """ Synchronizer for importing data from a backend to OpenERP """

    def _init_mapper(self, environment):
        model_name = environment.model_name
        get_class = self.backend.get_class
        self.mapper = get_class(ImportMapper, model_name)(environment)
