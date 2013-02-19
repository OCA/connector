# -*- encoding: utf-8 -*-
###############################################################################
#                                                                             #
#   base_external_referentials for OpenERP                                    #
#   Copyright (C) 2011 Akretion Sébastien BEAU <sebastien.beau@akretion.com>  #
#                                                                             #
#   This program is free software: you can redistribute it and/or modify      #
#   it under the terms of the GNU Affero General Public License as            #
#   published by the Free Software Foundation, either version 3 of the        #
#   License, or (at your option) any later version.                           #
#                                                                             #
#   This program is distributed in the hope that it will be useful,           #
#   but WITHOUT ANY WARRANTY; without even the implied warranty of            #
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the             #
#   GNU Affero General Public License for more details.                       #
#                                                                             #
#   You should have received a copy of the GNU Affero General Public License  #
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.     #
#                                                                             #
###############################################################################


class MappingError(Exception):
    def __init__(self, value, mapping_name, mapping_object):
        self.value = value
        self.mapping_name = mapping_name
        self.mapping_object = mapping_object
    def __str__(self):
        return 'the mapping line: %s for the object %s has this error: %s' % (self.mapping_name,
                                                                             self.mapping_object,
                                                                             self.value)


class ExtConnError(Exception):
     def __init__(self, value):
         self.value = value
     def __str__(self):
         return str(self.value)

