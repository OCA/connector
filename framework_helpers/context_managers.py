# -*- encoding: utf-8 -*-
#################################################################################
#                                                                               #
#    framework_helpers for OpenERP                                              #
#    Copyright (C) 2011 Akretion Benoît Guillot <benoit.guillot@akretion.com>   #
#                                                                               #
#    This program is free software: you can redistribute it and/or modify       #
#    it under the terms of the GNU Affero General Public License as             #
#    published by the Free Software Foundation, either version 3 of the         #
#    License, or (at your option) any later version.                            #
#                                                                               #
#    This program is distributed in the hope that it will be useful,            #
#    but WITHOUT ANY WARRANTY; without even the implied warranty of             #
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the              #
#    GNU Affero General Public License for more details.                        #
#                                                                               #
#    You should have received a copy of the GNU Affero General Public License   #
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.      #
#                                                                               #
#################################################################################

import pooler
from contextlib import contextmanager

@contextmanager
def commit_now(cr, logger, raise_error=False):
    """
    Context Manager to use in order to commit into a cursor
    correctly with a try/except method and a rollback if necessary
    :param cr cursor: cursor to commit
    :param logger logger: logger used to logging the message
    :param raise_error boolean: Set to true only if you want
             to stop the process if an error occured
    """
    try:
        yield cr
    except Exception, e:
        cr.rollback()
        logger.exception(e)
        if raise_error:
            raise
    else:
        cr.commit()

@contextmanager
def new_cursor(cr, logger, raise_error=False):
    """
    Context Manager to use in order to commit into a new cursor
    correctly with a try/except method and a rollback if necessary
    :param cr cursor: cursor to copy
    :param logger logger: logger used to logging the message
    :param raise_error boolean: Set to true only if you want
             to stop the process if an error occured
    """
    new_cr = pooler.get_db(cr.dbname).cursor()
    try:
        yield new_cr
    except Exception, e:
        new_cr.rollback()
        logger.exception(e)
        if raise_error:
            raise
    else:
        new_cr.commit()
    finally:
        new_cr.close()
