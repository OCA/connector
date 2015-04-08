# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2010-2015 Elico Corp (<http://www.elico-corp.com>)
#    Authors: Liu Lixia, Augustin Cisterne-Kaas
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
from openerp import models, fields
from openerp.addons.connector.connector import (Environment,
                                                install_in_connector)
from openerp.addons.connector.checkpoint import checkpoint

install_in_connector()


def get_environment(session, model_name, backend_id):
    """ Create an environment to work with.  """
    backend_record = session.browse('dns.backend', backend_id)
    env = Environment(backend_record, session, model_name)
    return env


class DNSBinding(models.Model):
    """ Abstract Model for the Bindigs.
    All the models used as bindings between dnspod and OpenERP
    (``dnspod.res.partner``, ``dnspod.product.product``, ...) should
    ``_inherit`` it.
    """
    _name = 'dns.binding'
    _inherit = 'external.binding'
    _description = 'dns Binding (abstract)'

    backend_id = fields.Many2one(
        'dns.backend',
        String='DNS Backend',
        required=True,
        ondelete='restrict')
    # fields.char because 0 is a valid dnspod ID
    dns_id = fields.Char('ID on other software')
    # state of the record synchronization with dnspod
    state = fields.Selection(
        [('draft', 'Draft'), ('done', 'Done'),
         ('exception', 'Exception')], 'State',
        default="draft",
        help='Done when succeed otherwise Exception')


def add_checkpoint(session, model_name, record_id, backend_id):
    """ Add a row in the model ``connector.checkpoint`` for a record,
    meaning it has to be reviewed by a user.
    :param session: current session
    :type session: :class:`openerp.addons.connector.session.ConnectorSession`
    :param model_name: name of the model of the record to be reviewed
    :type model_name: str
    :param record_id: ID of the record to be reviewed
    :type record_id: int
    :param backend_id: ID of the dnspod Backend
    :type backend_id: int
    """
    return checkpoint.add_checkpoint(session, model_name, record_id,
                                     'dns.backend', backend_id)
