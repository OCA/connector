# -*- coding: utf-8 -*-
# Copyright 2013-2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import models, fields, api
from . import backend


class ConnectorBackend(models.AbstractModel):
    """ An instance of an external backend to synchronize with.

    The backends have to ``_inherit`` this model in the connectors
    modules.
    """
    _name = 'connector.backend'
    _description = 'Connector Backend'
    _backend_type = None

    name = fields.Char(required=True)
    # replace by a selection in concrete models
    version = fields.Selection(selection=[], required=True)

    @api.multi
    def get_backend(self):
        """ For a record of backend, returns the appropriate instance
        of :py:class:`~connector.backend.Backend`.
        """
        self.ensure_one()
        if self._backend_type is None:
            raise ValueError('The backend %s has no _backend_type' % self)
        return backend.get_backend(self._backend_type, self.version)


class ExternalBinding(models.AbstractModel):
    """ An abstract model for bindings to external records.

    An external binding is a binding between a backend and Odoo.  For
    example, for a partner, it could be ``magento.res.partner`` or for a
    product, ``magento.product``.

    The final model, will be an ``_inherits`` of the Odoo model and
    will ``_inherit`` this model.

    It will have a relation to the record (via ``_inherits``) and to the
    concrete backend model (``magento.backend`` for instance).

    It will also contains all the data relative to the backend for the
    record.

    It needs to implements at least these fields:

    odoo_id

        The many2one to the record it links (used by ``_inherits``).

    backend_id

        The many2one to the backend (for instance ``magento.backend``).

    magento_id or prestashop_id or ...

        The ID on the backend.

    sync_date

        Last date of synchronization


    The definition of the relations in ``_columns`` is to be done in the
    concrete classes because the relations themselves do not exist in
    this addon.

    For example, for a ``res.partner.category`` from Magento, I would have
    (this is a consolidation of all the columns from the abstract models,
    in ``magentoerpconnect`` you would not find that)::

        class MagentoResPartnerCategory(models.Model):
            _name = 'magento.res.partner.category'

            _inherits = {'res.partner.category': 'odoo_id'}

            odoo_id = fields.Many2one(comodel_name='res.partner.category',
                                          string='Partner Category',
                                          required=True,
                                          ondelete='cascade')
            backend_id = fields.Many2one(
                comodel_name='magento.backend',
                string='Magento Backend',
                required=True,
                ondelete='restrict')
            magento_id = fields.Char(string='ID on Magento')
            tax_class_id = fields.Integer(string='Tax Class ID')

            _sql_constraints = [
                ('magento_uniq', 'unique(backend_id, magento_id)',
                 'Partner Tag with same ID on Magento already exists.'),
            ]


    """
    _name = 'external.binding'
    _description = 'External Binding (abstract)'

    sync_date = fields.Datetime(string='Last synchronization date')
    # add other fields in concrete models
