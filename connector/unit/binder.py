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


class Binder(ConnectorUnit):
    """ For one record of a model, capable to find an external or
    internal id, or create the link between them
    """

    _model_name = None  # define in sub-classes

    def to_openerp(self, external_id):
        """ Give the OpenERP ID for an external ID

        :param external_id: external ID for which we want
                                   the OpenERP ID
        :return: OpenERP ID of the record
        :rtype: int
        """
        raise NotImplementedError

    def to_backend(self, openerp_id):
        """ Give the external ID for an OpenERP ID

        :param openerp_id: OpenERP ID for which we want the backend id
        :return: external ID of the record
        """
        raise NotImplementedError

    def bind(self, external_id, openerp_id, metadata=None):
        """ Create the link between an external ID and an OpenERP ID

        :param external_id: external id to bind
        :param openerp_id: OpenERP ID to bind
        :type openerp_id: int
        :param metadata: optional values to store on the relation model
        :type metadata: dict
        """
        raise NotImplementedError

    def read_metadata(self, openerp_id, external_id):
        """ Read the metadata for a relation OpenERP - Backend """
        raise NotImplementedError
