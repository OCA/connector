# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    Sharoon Thomas, Raphaël Valyi
#    Copyright (C) 2011-2012 Camptocamp Guewen Baconnier
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from osv import fields, osv
import base64
import time
from datetime import datetime
import logging
import pooler

from message_error import MappingError, ExtConnError
from tools.translate import _
from tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT


class ExternalSession(object):
    def __init__(self, referential):
        self.referential_id = referential
        self.debug = referential.debug
        self.logger = logging.getLogger(referential.name)
        self.connection = referential.external_connection(debug=self.debug, logger = self.logger)

    def is_type(self, referential_type):
        return self.referential_id.type_id.name.lower() == referential_type.lower()

    def is_categ(self, referential_category):
        return self.referential_id.categ_id.name.lower() == referential_category.lower()


########################################################################################################################
#
#                                             BASIC FEATURES
#
########################################################################################################################


def read_w_order(self, cr, uid, ids, fields_to_read=None, context=None, load='_classic_read'):
    """ Read records with given ids with the given fields and return it respecting the order of the ids
    This is very usefull for synchronizing data in a special order with an external system

    :param list ids: list of the ids of the records to read
    :param list fields: optional list of field names to return (default: all fields would be returned)
    :param dict context: context arguments, like lang, time zone
    :return: ordered list of dictionaries((dictionary per record asked)) with requested field values
    :rtype: [{‘name_of_the_field’: value, ...}, ...]
    """
    res = self.read(cr, uid, ids, fields_to_read, context, load)
    resultat = []
    for id in ids:
        resultat += [x for x in res if x['id'] == id]
    return resultat

def browse_w_order(self, cr, uid, ids, context=None, list_class=None, fields_process={}):
    """Fetch records as objects and return it respecting the order of the ids
    This is very usefull for synchronizing data in a special order with an external system

    :param list ids: id or list of ids.
    :param dict context: context arguments, like lang, time zone
    :return: ordered list of object
    :rtype: list of objects requested
    """
    res = self.browse(cr, uid, ids, context, list_class, fields_process)
    resultat = []
    for id in ids:
        resultat += [x for x in res if x.id == id]
    return resultat

def prefixed_id(self, id):
    """The reason why we don't just use the external id and put the model as the prefix is to avoid unique ir_model_data#name per module constraint violation."""
    return self._name.replace('.', '_') + '/' + str(id)

def id_from_prefixed_id(self, prefixed_id):
    return prefixed_id.split(self._name.replace('.', '_') + '/')[1]


#======================================NOT USED ANYWHERE
def get_last_imported_external_id(self, cr, object_name, referential_id, where_clause):
    table_name = object_name.replace('.', '_')
    cr.execute("""
               SELECT %(table_name)s.id, ir_model_data.name from %(table_name)s inner join ir_model_data
               ON %(table_name)s.id = ir_model_data.res_id
               WHERE ir_model_data.model=%%s %(where_clause)s
                 AND ir_model_data.referential_id = %%s
               ORDER BY %(table_name)s.create_date DESC
               LIMIT 1
               """ % { 'table_name' : table_name, 'where_clause' : where_clause and ("and " + where_clause) or ""}
               , (object_name, referential_id,))
    results = cr.fetchone()
    if results and len(results) > 0:
        return [results[0], results[1].split(object_name.replace('.', '_') +'/')[1]]
    else:
        return [False, False]

#======================================NOT USED ANYWHERE
def get_modified_ids(self, cr, uid, date=False, context=None): 
    """ This function will return the ids of the modified or created items of self object since the date

    @return: a table of this format : [[id1, last modified date], [id2, last modified date] ...] """
    if date:
        sql_request = "SELECT id, create_date, write_date FROM %s " % (self._name.replace('.', '_'),)
        sql_request += "WHERE create_date > %s OR write_date > %s;"
        cr.execute(sql_request, (date, date))
    else:
        sql_request = "SELECT id, create_date, write_date FROM %s " % (self._name.replace('.', '_'),)
        cr.execute(sql_request)
    l = cr.fetchall()
    res = []
    for p in l:
        if p[2]:
            res += [[p[0], p[2]]]
        else:
            res += [[p[0], p[1]]]
    return sorted(res, key=lambda date: date[1])

def get_all_extid_from_referential(self, cr, uid, referential_id, context=None):
    """Returns the external ids of the ressource which have an ext_id in the referential"""
    ir_model_data_obj = self.pool.get('ir.model.data')
    model_data_ids = ir_model_data_obj.search(cr, uid, [('model', '=', self._name), ('referential_id', '=', referential_id)])
    #because OpenERP might keep ir_model_data (is it a bug?) for deleted records, we check if record exists:
    oeid_to_extid = {}
    for data in ir_model_data_obj.read(cr, uid, model_data_ids, ['res_id', 'name'], context=context):
        oeid_to_extid[data['res_id']] = self.id_from_prefixed_id(data['name'])
    if not oeid_to_extid:
        return []
    return [int(oeid_to_extid[oe_id]) for oe_id in self.exists(cr, uid, oeid_to_extid.keys(), context=context)]

def get_all_oeid_from_referential(self, cr, uid, referential_id, context=None):
    """Returns the openerp ids of the ressource which have an ext_id in the referential"""
    ir_model_data_obj = self.pool.get('ir.model.data')
    model_data_ids = ir_model_data_obj.search(cr, uid, [('model', '=', self._name), ('referential_id', '=', referential_id)])
    #because OpenERP might keep ir_model_data (is it a bug?) for deleted records, we check if record exists:
    claimed_oe_ids = [x['res_id'] for x in ir_model_data_obj.read(cr, uid, model_data_ids, ['res_id'], context=context)]
    return claimed_oe_ids and self.exists(cr, uid, claimed_oe_ids, context=context) or []

def oeid_to_extid(self, cr, uid, id, referential_id, context=None):
    """Returns the external id of a resource by its OpenERP id.
    Returns False if the resource id does not exists."""
    if isinstance(id, list):
        id = id[0]
    model_data_ids = self.pool.get('ir.model.data').search(cr, uid, [('model', '=', self._name), ('res_id', '=', id), ('referential_id', '=', referential_id)])
    if model_data_ids and len(model_data_ids) > 0:
        prefixed_id = self.pool.get('ir.model.data').read(cr, uid, model_data_ids[0], ['name'])['name']
        ext_id = self.id_from_prefixed_id(prefixed_id)
        return ext_id
    return False

def _extid_to_expected_oeid(self, cr, uid, referential_id, external_id, context=None):
    """
    Returns the id of the entry in ir.model.data and the expected id of the resource in the current model
    Warning the expected_oe_id may not exists in the model, that's the res_id registered in ir.model.data

    @param external_id: id in the external referential
    @param referential_id: id of the external referential
    @return: tuple of (ir.model.data entry id, expected resource id in the current model)
    """
    model_data_obj = self.pool.get('ir.model.data')
    model_data_ids = model_data_obj.search(cr, uid,
        [('name', '=', self.prefixed_id(external_id)),
         ('model', '=', self._name),
         ('referential_id', '=', referential_id)], context=context)
    model_data_id = model_data_ids and model_data_ids[0] or False
    expected_oe_id = False
    if model_data_id:
        expected_oe_id = model_data_obj.read(cr, uid, model_data_id, ['res_id'])['res_id']
    return model_data_id, expected_oe_id

def extid_to_existing_oeid(self, cr, uid, referential_id, external_id, context=None):
    """Returns the OpenERP id of a resource by its external id.
       Returns False if the resource does not exist."""
    if external_id:
        ir_model_data_id, expected_oe_id = self._extid_to_expected_oeid\
            (cr, uid, referential_id, external_id, context=context)
        # Note: OpenERP cleans up ir_model_data which res_id records have been deleted
        # only at server update because that would be a perf penalty, we returns the res_id only if
        # really existing and we delete the ir_model_data unused
        if expected_oe_id and self.exists(cr, uid, expected_oe_id, context=context):
            return expected_oe_id
        elif ir_model_data_id:
            # CHECK: do we have to unlink the result when we call to this method ? I propose just to ignore them
            # see method _existing_oeid_for_extid_import
            # the bad ir.model.data are cleaned up when we import again a external resource with the same id
            # So I see 2 cons points:
            # - perf penalty
            # - by doing an unlink, we are writing to the database even if we just need to read a record (what about locks?)
            self.pool.get('ir.model.data').unlink(cr, uid, ir_model_data_id, context=context)
    return False

def extid_to_oeid(self, cr, uid, external_session, external_id, context=None):
    """Returns the OpenERP ID of a resource by its external id.
    Creates the resource from the external connection if the resource does not exist."""
    #First get the external key field name
    #conversion external id -> OpenERP object using Object mapping_column_name key!
    if external_id:
        existing_id = self.extid_to_existing_oeid(cr, uid, external_session.referential_id.id, external_id, context=context)
        if existing_id:
            return existing_id
        #TODO try except will be added latter
        #try:
        if context and context.get('alternative_key', False): #FIXME dirty fix for Magento product.info id/sku mix bug: https://bugs.launchpad.net/magentoerpconnect/+bug/688225
            id = context.get('alternative_key', False)
            context['id'] 
        return self._import_one_resource(cr, uid, external_session, external_id, context=context)
        #except Exception, error: #external system might return error because no such record exists
        #    raise osv.except_osv(_('Ext Synchro'), _("Error when importing on fly the object %s with the external_id %s and the external referential %s.\n Error : %s" %(self._name, id, referential_id, error)))
    return False

#######################        MONKEY PATCHING       #######################

osv.osv.read_w_order = read_w_order
osv.osv.browse_w_order = browse_w_order

osv.osv.prefixed_id = prefixed_id
osv.osv.id_from_prefixed_id = id_from_prefixed_id
osv.osv.get_last_imported_external_id = get_last_imported_external_id
osv.osv.get_modified_ids = get_modified_ids
osv.osv.oeid_to_extid = oeid_to_extid
osv.osv._extid_to_expected_oeid = _extid_to_expected_oeid
osv.osv.extid_to_existing_oeid = extid_to_existing_oeid
osv.osv.extid_to_oeid = extid_to_oeid
osv.osv.get_all_oeid_from_referential = get_all_oeid_from_referential
osv.osv.get_all_extid_from_referential = get_all_extid_from_referential


########################################################################################################################
#
#                                             END OF BASIC FEATURES
#
########################################################################################################################





########################################################################################################################
#
#                                             IMPORT FEATURES
#
########################################################################################################################



def _get_filter(self, cr, uid, external_session, step, previous_filter=None, context=None):
    """
    Abstract function that return the filter
    Can be overwriten in your module

    :param ExternalSession external_session : External_session that contain all params of connection
    :param int step: Step the of the import, 100 meant you will import data per 100
    :param dict previous_filter: the previous filter
    :return: dictionary with a filter
    :rtype: dict
    """
    return None

def _get_external_resource_ids(self, cr, uid, external_session, resource_filter=None, mapping=None, context=None):
    """
    Abstract function that return the external resource ids
    Can be overwriten in your module

    :param ExternalSession external_session : External_session that contain all params of connection
    :param dict resource_filter: the filter to apply to the external search method
    :param dict mapping: dictionnary of mapping, the key is the openerp object's name 
    :return: a list of external_id
    :rtype: list
    """
    raise osv.except_osv(_("Not Implemented"), _("Not Implemented in abstract base module!"))

def _get_default_import_values(self, cr, uid, external_session, context=None):
    """
    Abstract function that return the default value for on object
    Can be overwriten in your module

    :param ExternalSession external_session : External_session that contain all params of connection
    :return: a dictionnary of default value
    :rtype: dict
    """
    return None

def _get_import_step(self, cr, uid, external_session, context=None):
    """
    Abstract function that return the step for importing data
    Can be overwriten in your module

    :param ExternalSession external_session : External_session that contain all params of connection
    :return: a integer that corespond to the limit of object to import
    :rtype: int
    """
    return 100

def _get_external_resources(self, cr, uid, external_session, external_id=None, resource_filter=None, mapping=None, fields=None, context=None):
    """
    Abstract function that return the external resource
    Can be overwriten in your module

    :param ExternalSession external_session : External_session that contain all params of connection
    :param int external_id : resource external id to import
    :param dict resource_filter: the filter to apply to the external search method
    :param dict mapping: dictionnary of mapping, the key is the openerp object's name
    :param list fields: list of field to read
    :return: a list of dict that contain resource information
    :rtype: list
    """
    raise osv.except_osv(_("Not Implemented"), _("Not Implemented in abstract base module!"))

def _get_mapping_id(self, cr, uid, referential_id, context=None):
    """
    Function that return the mapping id for the corresponding object

    :params int referential_id: the referential id
    :return the id of the mapping
    :rtype integer
    """
    mapping_id = self.pool.get('external.mapping').search(cr, uid, [('model', '=', self._name), ('referential_id', '=', referential_id)], context=context)
    return mapping_id and mapping_id[0] or False

def _init_mapping(self, cr, uid, referential_id, convertion_type='from_external_to_openerp', mapping_line_filter_ids=None, mapping=None, mapping_id=None, context=None):
    if not mapping:
        mapping={}
    if not mapping_id:
        mapping_id = self._get_mapping_id(cr, uid, referential_id, context=context)
    if not mapping.get(mapping_id):
        mapping[mapping_id] = self._get_mapping(cr, uid, referential_id, convertion_type=convertion_type, mapping_line_filter_ids=mapping_line_filter_ids, mapping_id=mapping_id, context=context)
    return mapping, mapping_id

def _get_mapping(self, cr, uid, referential_id, convertion_type='from_external_to_openerp', mapping_line_filter_ids=None, mapping_id=None, context=None):
    """
    Function that return the mapping line for the corresponding object

    :param  int referential_id: the referential id
    :return: dictionary with the key "mapping_lines" and "key_for_external_id"
    :rtype: dict
    """
    if not mapping_id:
        mapping_id = self._get_mapping_id(cr, uid, referential_id, context=context)
    if not mapping_id:
        raise osv.except_osv(_('External Import Error'), _("The object %s doesn't have an external mapping" %self._name))
    else:
        #If a mapping exists for current model, search for mapping lines

        mapping_type = convertion_type == 'from_external_to_openerp' and 'in' or 'out'
        mapping_line_filter = [('mapping_id', '=', mapping_id),
                            ('type', 'in', ['in_out', mapping_type])]
        if mapping_line_filter_ids:
            mapping_line_filter += ['|', ('id', 'in', mapping_line_filter_ids), ('evaluation_type', '=', 'sub-mapping')]
        mapping_line_ids = self.pool.get('external.mapping.line').search(cr, uid, mapping_line_filter, context=context)
        if mapping_line_ids:
            mapping_lines = self.pool.get('external.mapping.line').read(cr, uid, mapping_line_ids, [], context=context)
        else:
            mapping_lines = []

        res = self.pool.get('external.mapping').read(cr, uid, mapping_id, context=context)
        alternative_key = [x['internal_field'] for x in mapping_lines if x['alternative_key']]
        res['alternative_keys'] = alternative_key or False
        res['key_for_external_id'] = res['key_for_external_id'] or 'id'
        res['mapping_lines'] = mapping_lines
        return res

def import_resources(self, cr, uid, ids, resource_name, method="search_then_read", context=None):
    """
    Abstract function to import resources from a shop / a referential...

    :param list ids: list of id
    :param string ressource_name: the resource name to import
    :return: dictionary with the key "create_ids" and "write_ids" which containt the id created/written
    :rtype: dict
    """
    result = {"create_ids" : [], "write_ids" : []}
    for browse_record in self.browse(cr, uid, ids, context=context):
        if browse_record._name == 'external.referential':
            external_session = ExternalSession(browse_record)
        else:
            if hasattr(browse_record, 'referential_id'):
                context['%s_id'%browse_record._name] = browse_record.id
                external_session = ExternalSession(browse_record.referential_id)
            else:
                raise osv.except_osv(_("Not Implemented"), _("The field referential_id doesn't exist on the object %s. Reporting system can not be used" %(browse_record._name,)))
        defaults = self.pool.get(resource_name)._get_default_import_values(cr, uid, external_session, context=context)
        res = self.pool.get(resource_name)._import_resources(cr, uid, external_session, defaults, method=method, context=context)
        for key in result:
            result[key].append(res.get(key, []))
    return result

def _import_resources(self, cr, uid, external_session, defaults=None, method="search_then_read", context=None):
    """
    Abstract function to import resources form a specific object (like shop, referential...)

    :param ExternalSession external_session : External_session that contain all params of connection
    :param dict defaults: default value for the resource to create
    :param str method: method to use to import resource
    :return: dictionary with the key "create_ids" and "write_ids" which containt the id created/written
    :rtype: dict
    """
    external_session.logger.info("Start to import the ressource %s"%(self._name,))
    result = {"create_ids" : [], "write_ids" : []}
    mapping, mapping_id = self._init_mapping(cr, uid, external_session.referential_id.id, context=context)
    if mapping[mapping_id].get('mapping_lines'):
        step = self._get_import_step(cr, uid, external_session, context=context)
        resource_filter = None
        #TODO refactor improve and simplify this code
        if method == 'search_then_read':
            while True:
                resource_filter = self._get_filter(cr, uid, external_session, step, previous_filter=resource_filter, context=context)
                ext_ids = self._get_external_resource_ids(cr, uid, external_session, resource_filter, mapping=mapping, context=context)
                if not ext_ids:
                    break
                for ext_id in ext_ids:
                    #TODO import only the field needed to improve speed import ;)
                    resources = self._get_external_resources(cr, uid, external_session, ext_id, mapping=mapping, fields=None, context=context)
                    if not isinstance(resources, list):
                        resources = [resources]
                    res = self._record_external_resources(cr, uid, external_session, resources, defaults=defaults, mapping=mapping, mapping_id=mapping_id, context=context)
                    for key in result:
                        result[key].append(res.get(key, []))
        elif method == 'search_then_read_no_loop':
            #Magento API do not support step import so we can not use a loop
            resource_filter = self._get_filter(cr, uid, external_session, step, previous_filter=resource_filter, context=context)
            ext_ids = self._get_external_resource_ids(cr, uid, external_session, resource_filter, mapping=mapping, context=context)
            for ext_id in ext_ids:
                #TODO import only the field needed to improve speed import ;)
                resources = self._get_external_resources(cr, uid, external_session, ext_id, mapping=mapping, fields=None, context=context)
                if not isinstance(resources, list):
                    resources = [resources]
                res = self._record_external_resources(cr, uid, external_session, resources, defaults=defaults, mapping=mapping, mapping_id=mapping_id, context=context)
                for key in result:
                    result[key].append(res.get(key, []))
        elif method == 'search_read':
            while True:
                resource_filter = self._get_filter(cr, uid, external_session, step, previous_filter=resource_filter, context=context)
                #TODO import only the field needed to improve speed import ;)
                resources = self._get_external_resources(cr, uid, external_session, resource_filter=resource_filter, mapping=mapping, fields=None, context=context)
                if not resources:
                    break
                if not isinstance(resources, list):
                    resources = [resources]
                res = self._record_external_resources(cr, uid, external_session, resources, defaults=defaults, mapping=mapping, mapping_id=mapping_id, context=context)
                for key in result:
                    result[key].append(res.get(key, []))
        elif method == 'search_read_no_loop':
            #Magento API do not support step import so we can not use a loop
            resource_filter = self._get_filter(cr, uid, external_session, step, previous_filter=resource_filter, context=context)
            #TODO import only the field needed to improve speed import ;)
            resources = self._get_external_resources(cr, uid, external_session, resource_filter=resource_filter, mapping=mapping, fields=None, context=context)
            if not isinstance(resources, list):
                resources = [resources]
            res = self._record_external_resources(cr, uid, external_session, resources, defaults=defaults, mapping=mapping, mapping_id=mapping_id, context=context)
            for key in result:
                result[key].append(res.get(key, []))
    return result

def _import_one_resource(self, cr, uid, external_session, external_id, context=None):
    """
    Abstract function to import one resource

    :param ExternalSession external_session : External_session that contain all params of connection
    :param int external_id : resource external id to import
    :return: the openerp id of the resource imported
    :rtype: int
    """
    resources = self._get_external_resources(cr, uid, external_session, external_id, context=context)
    if isinstance(resources, list):
        res = self._record_external_resources(cr, uid, external_session, resources, context=context)
        id = res.get('write_ids') and res['write_ids'][0] or res['create_ids'][0]
    else:
        res = self._record_one_external_resource(cr, uid, external_session, resources, context=context)
        id = res.get('write_id') or res.get('create_id')
    return id




def _record_external_resources(self, cr, uid, external_session, resources, defaults=None, mapping=None, mapping_id=None, context=None):
    """
    Abstract function to record external resources (this will convert the data and create/update the object in openerp)

    :param ExternalSession external_session : External_session that contain all params of connection
    :param list resource: list of resource to import
    :param dict defaults: default value for the resource to create
    :param dict mapping: dictionnary of mapping, the key is the openerp object's name
    :return: dictionary with the key "create_ids" and "write_ids" which containt the id created/written
    :rtype: dict
    """
    result = {'write_ids': [], 'create_ids': []}
    mapping, mapping_id = self._init_mapping(cr, uid, external_session.referential_id.id, mapping=mapping, mapping_id=mapping_id, context=context)
    for resource in resources:
        res = self._record_one_external_resource(cr, uid, external_session, resource, defaults=defaults, mapping=mapping, mapping_id=mapping_id, context=context)
        if res.get('create_id'): result['create_ids'].append(res['create_id'])
        if res.get('write_id'): result['write_ids'].append(res['write_id'])
    return result


def _record_one_external_resource(self, cr, uid, external_session, resource, defaults=None, mapping=None, mapping_id=None, context=None):
    """
    Used in _record_external_resources
    The resource will converted into OpenERP data by using the function _transform_external_resources
    And then created or updated, and an external id will be added into the table ir.model.data

    :param dict resource: resource to convert into OpenERP data
    :param int referential_id: external referential id from where we import the resource
    :param dict defaults: defaults value
    :return: dictionary with the key "create_id" and "write_id" which containt the id created/written
    """
    mapping, mapping_id = self._init_mapping(cr, uid, external_session.referential_id.id, mapping=mapping, mapping_id=mapping_id, context=context)
    written = created = False
    vals = self._transform_one_resource(cr, uid, external_session, 'from_external_to_openerp', resource, mapping=mapping, mapping_id=mapping_id, defaults=defaults, context=context)

    referential_id = external_session.referential_id.id
    external_id = vals.get('external_id')
    external_id_ok = not (external_id is None or external_id is False)
    alternative_keys = mapping[mapping_id]['alternative_keys']
    existing_rec_id = False
    existing_ir_model_data_id = False
    if not (external_id is None or external_id is False):
        del vals['external_id']
        existing_ir_model_data_id, existing_rec_id = self._existing_oeid_for_extid_import\
            (cr, uid, vals, external_id, referential_id, context=context)
    if not existing_rec_id and alternative_keys:
        domain = []
        for alternative_key in alternative_keys:
            domain.append((alternative_key, '=', vals[alternative_key]))
        existing_rec_id = self.search(cr, uid, domain, context=context)
        existing_rec_id = existing_rec_id and existing_rec_id[0] or False

    if not (external_id_ok or alternative_keys):
        external_session.logger.warning(_("The object imported need an external_id, maybe the mapping doesn't exist for the object : %s" %self._name))

    if existing_rec_id:
        if self.oe_update(cr, uid, existing_rec_id, vals, referential_id, defaults=defaults, context=context):
            written = True
    else:
        existing_rec_id = self.oe_create(cr, uid, vals, referential_id, defaults, context=context)
        created = True

    if external_id_ok:
        if existing_ir_model_data_id:
            if created:
                # means the external ressource is registred in ir.model.data but the ressource doesn't exist
                # in this case we have to update the ir.model.data in order to point to the ressource created
                self.pool.get('ir.model.data').write(cr, uid, existing_ir_model_data_id, {'res_id': existing_rec_id}, context=context)
        else:
            ir_model_data_vals = \
            self.create_external_id_vals(cr, uid, existing_rec_id, external_id, referential_id, context=context)
            if not created:
                # means the external resource is bound to an already existing resource
                # but not registered in ir.model.data, we log it to inform the success of the binding
                external_session.logger.info("Bound in OpenERP %s from External Ref with "
                                            "external_id %s and OpenERP id %s successfully" %(self._name, external_id, existing_rec_id))

    if created:
        if external_id:
            external_session.logger.info(("Created in OpenERP %s from External Ref with"
                                    "external_id %s and OpenERP id %s successfully" %(self._name, external_id_ok and str(external_id), existing_rec_id)))
        elif alternative_keys:
            external_session.logger.info(("Created in OpenERP %s from External Ref with"
                                    "alternative_keys %s and OpenERP id %s successfully" %(self._name, external_id_ok and str (vals.get(alternative_keys)), existing_rec_id)))
        return {'create_id' : existing_rec_id}
    elif written:
        if external_id:
            external_session.logger.info(("Updated in OpenERP %s from External Ref with"
                                    "external_id %s and OpenERP id %s successfully" %(self._name, external_id_ok and str(external_id), existing_rec_id)))
        elif alternative_keys:
            external_session.logger.info(("Updated in OpenERP %s from External Ref with"
                                    "alternative_keys %s and OpenERP id %s successfully" %(self._name, external_id_ok and str (vals.get(alternative_keys)), existing_rec_id)))
        return {'write_id' : existing_rec_id}
    return {}



def retry_import(self, cr, uid, id, ext_id, referential_id, defaults=None, context=None):
    """ When we import again a previously failed import
    """
    raise osv.except_osv(_("Not Implemented"), _("Not Implemented in abstract base module!"))

def oe_update(self, cr, uid, existing_rec_id, vals, referential_id, defaults, context):
    return self.write(cr, uid, existing_rec_id, vals, context)

def oe_create(self, cr, uid, vals, referential_id, defaults, context):
    return self.create(cr, uid, vals, context)


#TODO rename this function DID WE STILL NEED IT??
def get_external_data(self, cr, uid, conn, referential_id, defaults=None, context=None):
    """Constructs data using WS or other synch protocols and then call ext_import on it"""
    return {'create_ids': [], 'write_ids': []}

#######################        MONKEY PATCHING       #######################

osv.osv.get_external_data = get_external_data

osv.osv.retry_import = retry_import
osv.osv._get_mapping = _get_mapping
osv.osv._get_mapping_id = _get_mapping_id
osv.osv._init_mapping = _init_mapping
osv.osv._get_default_import_values = _get_default_import_values
osv.osv._get_import_step = _get_import_step

osv.osv._get_filter = _get_filter
osv.osv._get_external_resources = _get_external_resources
osv.osv._get_external_resource_ids = _get_external_resource_ids

osv.osv.import_resources = import_resources
osv.osv._import_resources = _import_resources
osv.osv._import_one_resource = _import_one_resource

osv.osv._record_external_resources = _record_external_resources
osv.osv._record_one_external_resource = _record_one_external_resource
osv.osv.oe_update = oe_update
osv.osv.oe_create = oe_create

########################################################################################################################
#
#                                             END OF IMPORT FEATURES
#
########################################################################################################################




########################################################################################################################
#
#                                             EXPORT FEATURES
#
########################################################################################################################


def _export_resources_into_external_referential(self, cr, uid, external_session, ids, fields=[], defaults=None, context=None):
    mapping, mapping_id = self._init_mapping(cr, uid, external_session.referential_id.id, convertion_type='from_openerp_to_external', context=context)
    resources = self._get_oe_resources_into_external_format(cr, uid, external_session, ids, mapping=mapping, fields=fields, defaults=defaults, context=context)
    print 'TODO'
    return True

def _get_oe_resources_into_external_format(self, cr, uid, external_session, ids, mapping=None, mapping_line_filter_ids=None, fields=[], defaults=None, context=None):
    result = []
    for resource in self.read_w_order(cr, uid, ids, fields, context):
        result.append(self._transform_one_resource(cr, uid,  external_session, 'from_openerp_to_external', resource, mapping, mapping_line_filter_ids=mapping_line_filter_ids, parent_data=None, previous_result=None, defaults=defaults, context=context))
    return result

def _record_resourse_into_external_referential(self, cr, uid, external_session, resource, context=None):
    print 'TODO'
    return True





def _existing_oeid_for_extid_import(self, cr, uid, vals, external_id, referential_id, context=None):
    """
    Used in ext_import in order to search the OpenERP resource to update when importing an external resource.
    It searches the reference in ir.model.data and returns the id in ir.model.data and the id of the
    current's model resource, if it really exists (it may not exists, see below)

    As OpenERP cleans up ir_model_data which res_id records have been deleted only at server update
    because that would be a perf penalty, so we take care of it here.

    This method can also be used by inheriting, in order to find and bind resources by another way than ir.model.data when
    the resource is not already imported.
    As instance, search and bind partners by their mails. In such case, it must returns False for the ir_model_data.id and
    the partner to bind for the resource id

    @param vals: vals to create in OpenERP, already evaluated by _transform_one_external_resource
    @param external_id: external id of the resource to create
    @param referential_id: external referential id from where we import the resource
    @return: tuple of (ir.model.data id / False: external id to create in ir.model.data, model resource id / False: resource to create)
    """
    existing_ir_model_data_id, expected_res_id = self._extid_to_expected_oeid\
        (cr, uid, referential_id, external_id, context=context)

    # Take care of deleted resource ids, cleans up ir.model.data
    if existing_ir_model_data_id and expected_res_id and not self.exists(cr, uid, expected_res_id, context=context):
        self.pool.get('ir.model.data').unlink(cr, uid, existing_ir_model_data_id, context=context)
        existing_ir_model_data_id = expected_res_id = False
    return existing_ir_model_data_id, expected_res_id


#Deprecated
def extdata_from_oevals(self, cr, uid, referential_id, resource, mapping_lines, defaults, context=None):
    if context is None:
        context = {}
    vals = {} #Dictionary for record
    #Set defaults if any
    for each_default_entry in defaults.keys():
        vals[each_default_entry] = defaults[each_default_entry]
    for each_mapping_line in mapping_lines:
        #Build the space for expr
        space = {
            'self':self,
            'cr':cr,
            'uid':uid,
            'referential_id':referential_id,
            'defaults':defaults,
            'context':context,
            'record':resource,
            'conn':context.get('conn_obj', False),
            'base64':base64
        }
        #The expression should return value in list of tuple format
        #eg[('name','Sharoon'),('age',20)] -> vals = {'name':'Sharoon', 'age':20}
        if each_mapping_line['out_function']:
            try:
                exec each_mapping_line['out_function'] in space
            except Exception, e:
                logging.getLogger('external_synchro').exception("Error in import mapping: %r" % (each_mapping_line['out_function'],),
                                                                "Mapping Context: %r" % (space,),
                                                                "Exception: %r" % (e,))
                del(space['__builtins__'])
                raise MappingError(e, each_mapping_line['external_field'], self._name)
            result = space.get('result', False)
            #If result exists and is of type list
            if result:
                if isinstance(result, list):
                    for each_tuple in result:
                        if isinstance(each_tuple, tuple) and len(each_tuple) == 2:
                            vals[each_tuple[0]] = each_tuple[1]
                else:
                    raise MappingError(_('Invalid format for the variable result.'), each_mapping_line['external_field'], self._name)
    return vals

#Deprecated
def ext_export(self, cr, uid, ids, referential_ids=[], defaults={}, context=None):
    if context is None:
        context = {}
    #referential_ids has to be a list
    report_line_obj = self.pool.get('external.report.line')
    write_ids = []  #Will record ids of records modified, not sure if will be used
    create_ids = [] #Will record ids of newly created records, not sure if will be used
    for record_data in self.read_w_order(cr, uid, ids, [], context):
        #If no external_ref_ids are mentioned, then take all ext_ref_this item has
        if not referential_ids:
            ir_model_data_recids = self.pool.get('ir.model.data').search(cr, uid, [('model', '=', self._name), ('res_id', '=', id), ('module', 'ilike', 'extref')])
            if ir_model_data_recids:
                for each_model_rec in self.pool.get('ir.model.data').read(cr, uid, ir_model_data_recids, ['referential_id']):
                    if each_model_rec['referential_id']:
                        referential_ids.append(each_model_rec['referential_id'][0])
        #if still there no referential_ids then export to all referentials
        if not referential_ids:
            referential_ids = self.pool.get('external.referential').search(cr, uid, [])
        #Do an export for each external ID
        for ext_ref_id in referential_ids:
            #Find the mapping record now
            mapping_id = self.pool.get('external.mapping').search(cr, uid, [('model', '=', self._name), ('referential_id', '=', ext_ref_id)])
            if mapping_id:
                #If a mapping exists for current model, search for mapping lines
                mapping_line_ids = self.pool.get('external.mapping.line').search(cr, uid, [('mapping_id', '=', mapping_id[0]), ('type', 'in', ['in_out', 'out'])])
                mapping_lines = self.pool.get('external.mapping.line').read(cr, uid, mapping_line_ids, ['external_field', 'out_function'])
                if mapping_lines:
                    #if mapping lines exist find the data conversion for each row in inward data
                    exp_data = self.extdata_from_oevals(cr, uid, ext_ref_id, record_data, mapping_lines, defaults, context)
                    #Check if export for this referential demands a create or update
                    rec_check_ids = self.pool.get('ir.model.data').search(cr, uid, [('model', '=', self._name), ('res_id', '=', record_data['id']), ('module', 'ilike', 'extref'), ('referential_id', '=', ext_ref_id)])
                    #rec_check_ids will indicate if the product already has a mapping record with ext system
                    mapping_id = self.pool.get('external.mapping').search(cr, uid, [('model', '=', self._name), ('referential_id', '=', ext_ref_id)])
                    if mapping_id and len(mapping_id) == 1:
                        mapping_rec = self.pool.get('external.mapping').read(cr, uid, mapping_id[0], ['external_update_method', 'external_create_method'])
                        conn = context.get('conn_obj', False)
                        if rec_check_ids and mapping_rec and len(rec_check_ids) == 1:
                            ext_id = self.oeid_to_extid(cr, uid, record_data['id'], ext_ref_id, context)

                            if not context.get('force', False):#TODO rename this context's key in 'no_date_check' or something like that
                                #Record exists, check if update is required, for that collect last update times from ir.data & record
                                last_exported_times = self.pool.get('ir.model.data').read(cr, uid, rec_check_ids[0], ['write_date', 'create_date'])
                                last_exported_time = last_exported_times.get('write_date', False) or last_exported_times.get('create_date', False)
                                this_record_times = self.read(cr, uid, record_data['id'], ['write_date', 'create_date'])
                                last_updated_time = this_record_times.get('write_date', False) or this_record_times.get('create_date', False)

                                if not last_updated_time: #strangely seems that on inherits structure, write_date/create_date are False for children
                                    cr.execute("select write_date, create_date from %s where id=%s;" % (self._name.replace('.', '_'), record_data['id']))
                                    read = cr.fetchone()
                                    last_updated_time = read[0] and read[0].split('.')[0] or read[1] and read[1].split('.')[0] or False

                                if last_updated_time and last_exported_time:
                                    last_exported_time = datetime.datetime.fromtimestamp(time.mktime(time.strptime(last_exported_time[:19], DEFAULT_SERVER_DATETIME_FORMAT)))
                                    last_updated_time = datetime.datetime.fromtimestamp(time.mktime(time.strptime(last_updated_time[:19], DEFAULT_SERVER_DATETIME_FORMAT)))
                                    if last_exported_time + datetime.timedelta(seconds=1) > last_updated_time:
                                        continue

                            if conn and mapping_rec['external_update_method']:
                                try:
                                    self.ext_update(cr, uid, exp_data, conn, mapping_rec['external_update_method'], record_data['id'], ext_id, rec_check_ids[0], mapping_rec['external_create_method'], context)
                                    write_ids.append(record_data['id'])
                                    #Just simply write to ir.model.data to update the updated time
                                    ir_model_data_vals = {
                                                            'res_id': record_data['id'],
                                                          }
                                    self.pool.get('ir.model.data').write(cr, uid, rec_check_ids[0], ir_model_data_vals)
                                    report_line_obj.log_success(cr, uid, self._name, 'export',
                                                                res_id=record_data['id'],
                                                                external_id=ext_id, defaults=defaults,
                                                                context=context)
                                    logging.getLogger('external_synchro').info("Updated in External Ref %s from OpenERP with external_id %s and OpenERP id %s successfully" %(self._name, ext_id, record_data['id']))
                                except Exception, err:
                                    report_line_obj.log_failed(cr, uid, self._name, 'export',
                                                               res_id=record_data['id'],
                                                               external_id=ext_id, exception=err,
                                                               defaults=defaults, context=context)
                        else:
                            #Record needs to be created
                            if conn and mapping_rec['external_create_method']:
                                try:
                                    crid = self.ext_create(cr, uid, exp_data, conn, mapping_rec['external_create_method'], record_data['id'], context)
                                    create_ids.append(record_data['id'])
                                    self.create_external_id_vals(cr, uid, record_data['id'], crid, ext_ref_id, context=context)
                                    report_line_obj.log_success(cr, uid, self._name, 'export',
                                                                res_id=record_data['id'],
                                                                external_id=crid, defaults=defaults,
                                                                context=context)
                                    logging.getLogger('external_synchro').info("Created in External Ref %s from OpenERP with external_id %s and OpenERP id %s successfully" %(self._name, crid, record_data['id']))
                                except Exception, err:
                                    report_line_obj.log_failed(cr, uid, self._name, 'export',
                                                               res_id=record_data['id'],
                                                               exception=err, defaults=defaults,
                                                               context=context)
                        cr.commit()
    return {'create_ids': create_ids, 'write_ids': write_ids}

def _prepare_external_id_vals(self, cr, uid, res_id, ext_id, referential_id, context=None):
    """ Create an external reference for a resource id in the ir.model.data table"""
    ir_model_data_vals = {
                            'name': self.prefixed_id(ext_id),
                            'model': self._name,
                            'res_id': res_id,
                            'referential_id': referential_id,
                            'module': 'extref/' + self.pool.get('external.referential').\
                            read(cr, uid, referential_id, ['name'])['name']
                          }
    return ir_model_data_vals


def create_external_id_vals(self, cr, uid, existing_rec_id, external_id, referential_id, context=None):
    """Add the external id in the table ir_model_data"""
    ir_model_data_vals = \
    self._prepare_external_id_vals(cr, uid, existing_rec_id,
                                   external_id, referential_id,
                                   context=context)
    return self.pool.get('ir.model.data').create(cr, uid, ir_model_data_vals, context=context)


#TODO check if still needed?
def retry_export(self, cr, uid, id, ext_id, referential_id, defaults=None, context=None):
    """ When we export again a previously failed export
    """
    conn = self.pool.get('external.referential').external_connection(cr, uid, referential_id)
    context['conn_obj'] = conn
    return self.ext_export(cr, uid, [id], [referential_id], defaults, context)

#TODO check if still needed?
def can_create_on_update_failure(self, error, data, context):
    return True

#TODO check if still needed?
def ext_create(self, cr, uid, data, conn, method, oe_id, context):
    return conn.call(method, data)

#TODO check if still needed?
def try_ext_update(self, cr, uid, data, conn, method, oe_id, external_id, ir_model_data_id, create_method, context):
    return conn.call(method, [external_id, data])

#TODO check if still needed?
def ext_update(self, cr, uid, data, conn, method, oe_id, external_id, ir_model_data_id, create_method, context):
    try:
        self.try_ext_update(cr, uid, data, conn, method, oe_id, external_id, ir_model_data_id, create_method, context)
    except Exception, e:
        logging.getLogger('external_synchro').exception("UPDATE ERROR: %s" % e)
        if self.can_create_on_update_failure(e, data, context):
            logging.getLogger('external_synchro').info("The resource maybe doesn't exist any more in the external referential, trying to re-create a new one")
            crid = self.ext_create(cr, uid, data, conn, create_method, oe_id, context)
            self.pool.get('ir.model.data').write(cr, uid, ir_model_data_id, {'name': self.prefixed_id(crid)})
            return crid


#######################        MONKEY PATCHING       #######################

osv.osv._export_resources_into_external_referential = _export_resources_into_external_referential
osv.osv._get_oe_resources_into_external_format = _get_oe_resources_into_external_format
osv.osv._record_resourse_into_external_referential =_record_resourse_into_external_referential

osv.osv._existing_oeid_for_extid_import = _existing_oeid_for_extid_import

osv.osv.extdata_from_oevals = extdata_from_oevals
osv.osv.ext_export = ext_export

osv.osv.retry_export = retry_export
osv.osv.can_create_on_update_failure = can_create_on_update_failure
osv.osv.ext_create = ext_create
osv.osv.try_ext_update = try_ext_update
osv.osv.ext_update = ext_update

osv.osv._prepare_external_id_vals = _prepare_external_id_vals

osv.osv.create_external_id_vals = create_external_id_vals


########################################################################################################################
#
#                                             END OF EXPORT FEATURES
#
########################################################################################################################





########################################################################################################################
#
#                                             GENERIC TRANSFORM FEATURES
#
########################################################################################################################

def _transform_resources(self, cr, uid, external_session, convertion_type, resources, defaults=None, mapping=None, mapping_id=None, mapping_line_filter_ids=None, parent_data=None, context=None):
    """
    Used in ext_import in order to convert all of the external data into OpenERP data

    @param external_data: list of external_data to convert into OpenERP data
    @param referential_id: external referential id from where we import the resource
    @param parent_data: data of the parent, only use when a mapping line have the type 'sub mapping'
    @param defaults: defaults value for data converted
    @return: list of the line converted into OpenERP value
    """
    result= []
    if resources:
        mapping, mapping_id = self._init_mapping(cr, uid, external_session.referential_id.id, convertion_type=convertion_type, mapping_line_filter_ids=mapping_line_filter_ids, mapping=mapping, mapping_id=mapping_id, context=context)
        if convertion_type == 'from_openerp_to_external':
            field_to_read = [x['internal_field'] for x in mapping[mapping_id]['mapping_lines']]
            resources = self.read(cr, uid, resources, field_to_read, context=context)
        if mapping[mapping_id].get("mapping_lines"):
            for resource in resources:
                result.append(self._transform_one_resource(cr, uid, external_session, convertion_type, resource, 
                                                            mapping, mapping_id, mapping_line_filter_ids, parent_data=parent_data, 
                                                            previous_result=result, defaults=defaults, context=context))
    return result

def _transform_one_resource(self, cr, uid, external_session, convertion_type, resource, mapping, mapping_id, mapping_line_filter_ids=None, parent_data=None, previous_result=None, defaults=None, context=None):
    """
    Used in _transform_external_resources in order to convert external row of data into OpenERP data

    @param referential_id: external referential id from where we import the resource
    @param resource: a dictionnary of data to convert into OpenERP data
    @param mapping dict: dictionnary of mapping {'product.product' : {'mapping_lines' : [...], 'key_for_external_id':'...'}}
    @param previous_result: list of the previous line converted. This is not used here but it's necessary for playing on change on sale order line
    @param defaults: defaults value for the data imported
    @return: dictionary of converted data in OpenERP format 
    """


    if context is None:
        context = {}
    if defaults is None:
        defaults = {}
    mapping_lines = mapping[mapping_id].get("mapping_lines")
    key_for_external_id = mapping[mapping_id].get("key_for_external_id")

    vals = {} #Dictionary for create record
    sub_mapping_list=[]
    for mapping_line in mapping_lines:
        if convertion_type == 'from_external_to_openerp':
            from_field = mapping_line['external_field']
            if not from_field:
                from_field = "%s_%s" %(mapping_line['child_mapping_id'][1], mapping_line['child_mapping_id'][0])
            to_field = mapping_line['internal_field']
            to_field = mapping_line['internal_field']

        elif convertion_type == 'from_openerp_to_external':
            from_field = mapping_line['internal_field']
            to_field = mapping_line['external_field']

        if from_field in resource.keys():
            field_value = resource[from_field]
            if mapping_line['evaluation_type'] == 'sub-mapping':
                sub_mapping_list.append(mapping_line)
            else:
                if mapping_line['evaluation_type'] == 'direct':
                    vals[to_field] = self._transform_field(cr, uid, external_session, convertion_type, field_value, mapping_line, context=context)
                else:
                    #Build the space for expr
                    space = {'self': self,
                             'cr': cr,
                             'uid': uid,
                             'external_session': external_session,
                             'data': resource,
                             'referential_id': external_session.referential_id.id,
                             'defaults': defaults,
                             'context': context,
                             'ifield': self._transform_field(cr, uid, external_session, convertion_type, field_value, mapping_line, context=context),
                             'conn': context.get('conn_obj', False),
                             'base64': base64,
                             'vals': vals,
                             'previous_result': previous_result,
                        }

                    #The expression should return value in list of tuple format
                    #eg[('name','Sharoon'),('age',20)] -> vals = {'name':'Sharoon', 'age':20}
                    if convertion_type == 'from_external_to_openerp':
                        mapping_function_key = 'in_function'
                    else:
                        mapping_function_key = 'out_function'
                    try:
                        exec mapping_line[mapping_function_key] in space
                    except Exception, e:
                        external_session.logger.error("Error in import mapping: %r" % (mapping_line[mapping_function_key],),
                                                                           "Mapping Context: %r" % (space,),
                                                                           "Exception: %r" % (e,))
                        #del(space['__builtins__'])
                        raise MappingError(e, mapping_line['external_field'], self._name)
                    
                    result = space.get('result', False)
                    # Check if result returned by the mapping function is correct : [('field1', value), ('field2', value))]
                    # And fill the vals dict with the results
                    if result:
                        if isinstance(result, list):
                            for each_tuple in result:
                                if isinstance(each_tuple, tuple) and len(each_tuple) == 2:
                                    vals[each_tuple[0]] = each_tuple[1]
                        else:
                            raise MappingError(_('Invalid format for the variable result.'), mapping_line['external_field'], self._name)

    if convertion_type == 'from_external_to_openerp' and key_for_external_id and resource.get(key_for_external_id):
        ext_id = resource[key_for_external_id]
        vals.update({'external_id': ext_id.isdigit() and int(ext_id) or ext_id})
    vals = self._merge_with_default_values(cr, uid, external_session, resource, vals, sub_mapping_list, defaults=defaults, context=context)
    vals = self._transform_sub_mapping(cr, uid, external_session, convertion_type, resource, vals, sub_mapping_list, mapping, mapping_line_filter_ids=mapping_line_filter_ids, defaults=defaults, context=context)
    return vals

def _transform_field(self, cr, uid, external_session, convertion_type, field_value, mapping_line, context=None):
    field = False
    external_type = mapping_line['external_type']
    internal_type = mapping_line['internal_type']
    internal_field = mapping_line['internal_field']
    if field_value:
        if internal_type == 'many2one' and mapping_line['evaluation_type']=='direct':
            if external_type not in ['int', 'unicode']:
                raise osv.except_osv(_('User Error'), _('Wrong external type for mapping %s. One2Many object must have for external type string or integer')%(mapping_line['name'],))
            related_obj_name = self._columns[internal_field]._obj
            related_obj = self.pool.get(related_obj_name)
            if convertion_type == 'from_external_to_openerp':
                if external_type == 'unicode':
                    #TODO it can be great if we can search on other field
                    related_obj.search(cr, uid, [(related_obj._rec_name, '=', field_value)], context=context)
                else:
                    return related_obj.extid_to_oeid(cr, uid, external_session, field_value, context=context)
            else:
                if external_type == 'unicode':
                    #TODO it can be great if we can return on other field and not only the name
                    return field_value[1]
                else:
                    return related_obj.extid_to_oeid(cr, uid, external_session, field_value[0], context=context)

        elif external_type == "datetime":
            datetime_format = mapping_line['datetime_format']
            if convertion_type == 'from_external_to_openerp':
                datetime_value = datetime.strptime(field_value, datetime_format)
                if internal_type == 'date':
                    return datetime_value.strftime(DEFAULT_SERVER_DATE_FORMAT)
                elif internal_type == 'datetime':
                    return datetime_value.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
            else:
                if internal_type == 'date':
                    datetime_value = datetime.strptime(field_value, DEFAULT_SERVER_DATE_FORMAT)
                elif internal_type == 'datetime':
                    datetime_value = datetime.strptime(field_value, DEFAULT_SERVER_DATETIME_FORMAT)
                return datetime.strptime(datetime_value, datetime_format)

        elif external_type == 'list' and isinstance(field_value, (str, unicode)):
            # external data sometimes returns ',1,2,3' for a list...
            casted_field = eval(field_value.strip(','))
            # For a list, external data may returns something like '1,2,3' but also '1' if only
            # one item has been selected. So if the casted field is not iterable, we put it in a tuple: (1,)
            if not hasattr(casted_field, '__iter__'):
                casted_field = (casted_field,)
            field = list(casted_field)
        else:
            if external_type == 'float' and isinstance(field_value, (str, unicode)):
                field_value = field_value.replace(',','.')
            field = eval(external_type)(field_value)

    if field in ['None', 'False']:
        field = False

    #Set correct null value for each type
    if field is False or field is None:
        null_value = {
            'unicode': '', 
            'int': 0,
            'float': 0,
            'list': [],
            'dict': {},
        }
        if convertion_type == 'from_external_to_openerp':
            null_value['datetime'] = False
        else:
            null_value['datetime'] = ''
    return field

def _merge_with_default_values(self, cr, uid, external_session, ressource, vals, sub_mapping_list, defaults=None, context=None):
    """
    Used in _transform_one_external_resource in order to merge the defaults values, some params are useless here but need in base_sale_multichannels to play the on_change

    @param sub_mapping_list: list of sub-mapping to apply
    @param external_data: list of data to convert into OpenERP data
    @param referential_id: external referential id from where we import the resource
    @param vals: dictionnary of value previously converted
    @param defauls: defaults value for the data imported
    @return: dictionary of converted data in OpenERP format 
    """
    for key in defaults:
        if not key in vals:
            vals[key] = defaults[key]
    return vals

def _transform_sub_mapping(self, cr, uid, external_session, convertion_type, resource, vals, sub_mapping_list, mapping, mapping_line_filter_ids=None, defaults=None, context=None):
    """
    Used in _transform_one_external_resource in order to call the sub mapping

    @param sub_mapping_list: list of sub-mapping to apply
    @param external_data: list of data to convert into OpenERP data
    @param referential_id: external referential id from where we import the resource
    @param vals: dictionnary of value previously converted
    @param defauls: defaults value for the data imported
    @return: dictionary of converted data in OpenERP format 
    """

    if not defaults:
        defaults={}
    ir_model_field_obj = self.pool.get('ir.model.fields')
    for sub_mapping in sub_mapping_list:
        sub_object_name = sub_mapping['child_mapping_id'][1]
        mapping_id = sub_mapping['child_mapping_id'][0]
        if convertion_type == 'from_external_to_openerp':
            from_field = sub_mapping['external_field']
            if not from_field:
                from_field = "%s_%s" %(sub_object_name, mapping_id)
            to_field = sub_mapping['internal_field']
            field_value = resource[from_field]

        elif convertion_type == 'from_openerp_to_external':
            from_field = sub_mapping['internal_field']
            to_field = sub_mapping['external_field'] or 'hidden_field_to_split_%s'%from_field # if the field doesn't have any name we assume at that we will split it
            #Before calling submapping o2m resource must be an int and not a list of (id, name)
            if sub_mapping['external_type'] == 'many2one':
                field_value = resource[from_field] and resource[from_field][0] or False
            else:
                field_value = resource[from_field]

        if field_value:
            if sub_mapping['internal_type'] in ['one2many', 'many2many']:
                vals[to_field] = []
                lines = self.pool.get(sub_object_name)._transform_resources(cr, uid, external_session, convertion_type, field_value, defaults=defaults.get(to_field), mapping=mapping, mapping_id=mapping_id, mapping_line_filter_ids=mapping_line_filter_ids, parent_data=vals, context=context)
                for line in lines:
                    if 'external_id' in line:
                        del line['external_id']
                    if convertion_type == 'from_external_to_openerp':
                        vals[to_field].append((0, 0, line))
                    else:
                        vals[to_field].append(line)
            elif sub_mapping['internal_type'] == 'many2one':
                res = self.pool.get(sub_object_name)._record_one_external_resource(cr, uid, external_session, field_value, defaults=defaults.get(to_field), mapping=mapping, mapping_id=mapping_id, context=context)
                vals[to_field] = res.get('write_id') or res.get('create_id')
            else:
                vals[to_field] = self.pool.get(sub_object_name)._transform_resources(cr, uid, external_session, convertion_type, [field_value], defaults=defaults.get(to_field), mapping=mapping, mapping_id=mapping_id, mapping_line_filter_ids=mapping_line_filter_ids, parent_data=vals, context=context)[0]

    return vals

#TODO check if still needed?
def report_action_mapping(self, cr, uid, context=None):
    """
    For each action logged in the reports, we associate
    the method to launch when we replay the action.
    """
    mapping = {
        'export': {'method': self.retry_export, 
                   'fields': {'id': 'log.res_id',
                              'ext_id': 'log.external_id',
                              'referential_id': 'log.external_report_id.referential_id.id',
                              'defaults': 'log.origin_defaults',
                              'context': 'log.origin_context',
                              },
                },
        'import': {'method': self.retry_import,
                   'fields': {'id': 'log.res_id',
                              'ext_id': 'log.external_id',
                              'referential_id': 'log.external_report_id.referential_id.id',
                              'defaults': 'log.origin_defaults',
                              'context': 'log.origin_context',
                              },
                }
    }
    return mapping

#######################        MONKEY PATCHING       #######################

osv.osv._transform_resources = _transform_resources
osv.osv._transform_one_resource = _transform_one_resource
osv.osv._transform_sub_mapping = _transform_sub_mapping
osv.osv._merge_with_default_values = _merge_with_default_values
osv.osv._transform_field =_transform_field
osv.osv.report_action_mapping = report_action_mapping

########################################################################################################################
#
#                                           END GENERIC TRANSFORM FEATURES
#
########################################################################################################################




