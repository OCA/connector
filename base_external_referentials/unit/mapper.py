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

# directions
TO_REFERENCE = 'to_reference'
FROM_REFERENCE = 'from_reference'

from ..connector import ConnectorUnit


class Mapper(ConnectorUnit):
    """ Transform a record to a defined output """

    # name of the OpenERP model, to be defined in concrete classes
    model_name = None
    # direction of the conversion (TO_REFERENCE or FROM_REFERENCE)
    direction = None


class ImportMapper(Mapper):
    """ Transform a record from a backend to an OpenERP record """
    direction = FROM_REFERENCE


class ExportMapper(Mapper):
    """ Transform a record from OpenERP to a backend record """
    direction = TO_REFERENCE

