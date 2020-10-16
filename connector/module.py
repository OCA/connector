# -*- coding: utf-8 -*-
##############################################################################
#
#    Author: Guewen Baconnier
#    Copyright 2012-2013 Camptocamp SA
#    Copyright 2015 anybox SA
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

from openerp import models
from openerp.tools.cache import ormcache


class IrModuleModule(models.Model):
    """Overwrite ir.module.module to add cached method 'is_module_installed'.
    This method is cached, because connector will always check if a module is
    installed before do action.

    The next methods change the state of the module, then they must invalidate
    the cache of 'is_module_installed' method:

    * state_update
    * module_uninstall

    """
    _inherit = 'ir.module.module'

    @ormcache(skiparg=1)
    def is_module_installed(self, module_name):
        return bool(len(self.env['ir.module.module'].search([
            ('name', '=', module_name),
            ('state', '=', 'installed')])))

    def state_update(self, *args, **kwargs):
        res = super(IrModuleModule, self).state_update(*args, **kwargs)
        self.clear_caches()
        return res

    def module_uninstall(self, *args, **kwargs):
        res = super(IrModuleModule, self).module_uninstall(*args, **kwargs)
        self.clear_caches()
        return res
