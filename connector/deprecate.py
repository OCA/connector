# -*- coding: utf-8 -*-
##############################################################################
#
#    Author: Guewen Baconnier
#    Copyright 2015 Camptocamp SA
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

import inspect
import logging


def log_deprecate(message):
    # get the caller of the deprecated method
    frame, __, lineno, funcname, __, __ = inspect.stack()[2]
    module = inspect.getmodule(frame)
    logger = logging.getLogger(module.__name__)
    logger.warning('Deprecated: %s at line %r: %s', funcname, lineno, message)


class DeprecatedClass(object):

    def __init__(self, oldname, replacement):
        self.oldname = oldname
        self.replacement = replacement

    def _warning(self):
        frame, __, lineno, funcname, __, __ = inspect.stack()[2]
        module = inspect.getmodule(frame)
        logger = logging.getLogger(module.__name__)
        lineno = lineno
        logger.warning('Deprecated: class %s must be replaced by %s '
                       'at line %r',
                       self.oldname,
                       self.replacement.__name__,
                       lineno)

    def __call__(self, *args, **kwargs):
        self._warning()
        return self.replacement(*args, **kwargs)

    def __getattr__(self, *args, **kwargs):
        return getattr(self.replacement, *args, **kwargs)
