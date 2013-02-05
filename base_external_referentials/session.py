# -*- coding: utf-8 -*-
##############################################################################
#
#    Author: Guewen Baconnier
#    Copyright 2012 Camptocamp SA
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

import copy
import openerp.pooler

from contextlib import contextmanager


class ConnectorSession(object):
    """ Container for the OpenERP transactional stuff:

    .. attribute:: dbname

        The name of the database we're working on

    .. attribute:: cr

        The OpenERP Cursor

    .. attribute:: uid

        The User ID as integer

    .. attribute:: pool

        The registry of models

    .. attribute:: context

        The current OpenERP's context

    .. attribute:: model_name

        Name of the model we're working on

    .. attribute:: model

        Instance of the model we're working on

    A session can hold a reference to a model. This is useful
    in the connectors' context because a session's life is usually
    focused on a model (export a product, import a sale order, ...)

    There is 2 usages of a sessions:

    * use the session as a container for the current cursor and the
      other attributes
    * open / close transactions using a session

    When you already have a cursor and want to encapsulate it in a
    `Session`::

        session = ConnectorSession(cr, uid, pool, context=context)

    In this case, you must not commit, rollback or close the cursor.

    When you want to manage yourself the transaction, you can create a
    session without attaching a cursor and start a transaction using::

        session = ConnectorSession(cr.dbname, uid, context=context)
        with session.transaction():
            # work, work, work
            # self.cr and self.pool are now defined

    """

    @classmethod
    def use_existing_cr(cls, cr, uid, pool, model_name=None, context=None):
        """ The session will be initialized with the current ``Cursor``
        and ``pool`` of models, thus, it can be used as a container for the
        current transaction.
        """
        session = cls(cr.dbname, uid, model_name, context)
        session._cr = cr
        session.pool = pool
        return session

    def __init__(self, dbname, uid, model_name=None, context=None):
        self.dbname = dbname
        self._cr = None
        self.pool = None
        self.uid = uid
        self.model_name = model_name
        if context is None:
            context = {}
        self.context = context

    @property
    def cr(self):
        """ OpenERP Cursor """
        assert self._cr is not None, "No cursor"
        return self._cr

    @property
    def model(self):
        """ OpenERP Model """
        assert self.pool is not None, "No pool"
        assert self.model_name, "No model name"
        return self.pool.get(self.model_name)

    @contextmanager
    def change_user(self, uid):
        """ Temporarily change the user's session and restablish the
        normal user at closing,
        """
        current_uid = self.uid
        self.uid = uid
        yield self
        self.uid = current_uid

    @contextmanager
    def transaction(self):
        """ Start a new transaction and ensure that it is:

        * rollbacked on errors
        * commited at the end of the ``with`` context when no error occured
        * always closed at the end of the ``with`` context

        A transaction cannot be started if another one is already
        running on the session.
        """
        assert self._cr is None, "Transaction already started."
        db, self.pool = openerp.pooler.get_db_and_pool(self.dbname)
        self._cr = db.cursor()
        try:
            yield self
        except:
            self.rollback()
            raise
        else:
            self.commit()
        finally:
            self.close()
            self._cr = None
            self.pool = None

    def commit(self):
        """ Commit the cursor """
        self.cr.commit()

    def rollback(self):
        """ Rollback the cursor """
        self.cr.rollback()

    def close(self):
        """ Close the cursor """
        self.cr.close()

    def __copy__(self):
        return ConnectorSession(self.dbname,
                                self.uid,
                                self.model_name,
                                context=self.context)

    def __deepcopy__(self):
        return ConnectorSession(self.dbname,
                                self.uid,
                                self.model_name,
                                context=copy.deepcopy(self.context))
