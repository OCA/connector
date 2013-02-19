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


# TODO abstract external.referential
# TODO store and read metadata (attributes stored on the relation
# between the backend and the openerp record)
class Binder(ConnectorUnit):
    """ For one record of a model, capable to find an external or
    internal id, or create the link between them
    """

    _model_name = None  # define in sub-classes

    def __init__(self, reference, session):
        super(Binder, self).__init__(reference)
        self.session = session
        self.model = self.session.pool.get(self.model_name)

    def to_openerp(self, backend, backend_identifier):
        """ Give the OpenERP ID for an external ID

        :param backend: external backend
        :param backend_identifier: backend identifiers for which we want
                                   the OpenERP ID
        :type backend_identifier: :py:class:`connector.connector.RecordIdentifier`
        :return: OpenERP ID of the record
        :rtype: int
        """
        raise NotImplementedError

    def to_backend(self, backend, openerp_id):
        """ Give the backend ID for an OpenERP ID

        :param backend: browse of the external backend
        :param openerp_id: OpenERP ID for which we want the backend id
        :return: backend identifier of the record
        :rtype: :py:class:`connector.connector.RecordIdentifier`
        """
        raise NotImplementedError

    def bind(self, backend, backend_identifier, openerp_id):
        """ Create the link between an external ID and an OpenERP ID

        :param backend: browse of the external backend
        :param backend_identifier: Backend identifiers to bind
        :type backend_identifier: :py:class:`connector.connector.RecordIdentifier`
        :param openerp_id: OpenERP ID to bind
        :type openerp_id: int
        """
        raise NotImplementedError
