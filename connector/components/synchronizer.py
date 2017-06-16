# -*- coding: utf-8 -*-
# Copyright 2013-2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo.addons.component.core import AbstractComponent


class Synchronizer(AbstractComponent):
    """ Base class for synchronizers """

    _name = 'base.synchronizer'
    _inherit = 'base.connector'
    _usage = 'synchronizer'

    _base_mapper_usage = 'mapper'
    _base_backend_adapter_usage = 'backend.adapter'

    def __init__(self, work_context):
        super(Synchronizer, self).__init__(work_context)
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

        :rtype: :py:class:`connector.component.mapper.Mapper`
        """
        if self._mapper is None:
            self._mapper = self.component(usage=self._base_mapper_usage)
        return self._mapper

    @property
    def binder(self):
        """ Return an instance of ``Binder`` for the synchronization.

        The instanciation is delayed because some synchronisations do
        not need such an unit and the unit may not exist.

        :rtype: :py:class:`connector.component.binder.Binder`
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

        :rtype: :py:class:`connector.component.backend_adapter.BackendAdapter`
        """
        if self._backend_adapter is None:
            self._backend_adapter = self.component(
                usage=self._base_backend_adapter_usage
            )
        return self._backend_adapter


class Exporter(AbstractComponent):
    """ Synchronizer for exporting data from Odoo to a backend """

    _name = 'base.exporter'
    _inherit = 'base.synchronizer'
    _usage = 'exporter'
    _base_mapper_usage = 'export.mapper'


class Importer(AbstractComponent):
    """ Synchronizer for importing data from a backend to Odoo """

    _name = 'base.importer'
    _inherit = 'base.synchronizer'
    _usage = 'importer'
    _base_mapper_usage = 'import.mapper'


class Deleter(AbstractComponent):
    """ Synchronizer for deleting a record on the backend """

    _name = 'base.deleter'
    _inherit = 'base.synchronizer'
    _usage = 'deleter'