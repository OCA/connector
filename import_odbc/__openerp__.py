# -*- coding: utf-8 -*-
##############################################################################
#
#    Daniel Reis
#    2011
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

{
    'name': 'Import data from ODBC sources.',
    'version': '61.3',
    'category': 'Tools',
    'description': """
Import data directly from other databases.

Installed in the Administration module, menu Configuration -> Import from ODBC.

Features:
 * Fetched data from the databases are used to build lines equivalent to regular import files. These are imported using the standard "import_data()" ORM method, benefiting from all its features, including xml_ids.
 * Each table import is defined by an SQL statement, used to build the equivalent for an import file. Each column's name should match the column names you would use in an import file. The first column must provide an unique identifier for the record, and will be used to build its xml_id.
 * The last sync date is the last (successfull) execution. You can select only records changed since the last execution by adding a WHERE clause using this date with the representation "%s".
 * When errors are found, only the record with the error fails import. The other correct records are commited. However, the "last sync date" will only be automaticaly updated when no errors are found.
 * The import execution can be scheduled to run automatically.

Example SQL:
SELECT PRODUCT_CODE as "ref", PRODUCT_NAME as "name", 'res_partner_id_'+SUPPLIER_ID as "partner_id/id"
FROM T_PRODUCTS 
WHERE DATE_CHANGED >= %s
    """,
    'author': 'Daniel Reis',
    'website': 'http://launchpad.net/addons-tko',
    'images': [
        'images/snapshot1.png',
        'images/snapshot2.png',
    ],
    'depends': [
        'base',
        'base_external_dbsource',
    ],
    'init': [],
    'data': [
        'import_odbc_view.xml',
        'security/ir.model.access.csv',
    ],
    'demo': [],
    'test': [], 
    'installable': True,
    'active': False,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
