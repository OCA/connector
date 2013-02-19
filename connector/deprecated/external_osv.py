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

from openerp.osv.orm import Model
from openerp.osv.osv import except_osv
import base64
import urllib
import time
import openerp.netsvc
from datetime import datetime
import logging
from lxml import objectify
from openerp.tools.config import config

from message_error import MappingError, ExtConnError
from openerp.tools.translate import _
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT
#TODO fix me import do not work

#TODO refactor the mapping are stored in a dictionnary to avoid useless read during all of the process.
#It should be better to use the orm cache or something similare


def extend(class_to_extend):
    """
    Decorator to use to extend a existing class with a new method
    Example :
    @extend(Model)
    def new_method(self, *args, **kwargs):
        print 'I am in the new_method', self._name
        return True
    Will add the method new_method to the class Model
    """
    def decorator(func):
        if hasattr(class_to_extend, func.func_name):
            raise except_osv(_("Developper Error"),
                _("You can extend the class %s with the method %s.",
                "Indeed this method already exist use the decorator 'replace' instead"))
        setattr(class_to_extend, func.func_name, func)
        return class_to_extend
    return decorator

def override(class_to_extend, prefix):
    """
    Decorator for overiding an existing method in a class

    Example of use:

    @override(Model, 'magento_')
    def write(self, *args, **kwargs):
        print 'I am in the write overwrited 1', self._name
        return Model.magento_write(self, *args, **kwargs)

    @override(Model, 'amazon_')
    def write(self, *args, **kwargs):
        print 'I am in the write overwrited 2', self._name
        return Model.amazon_write(self, *args, **kwargs)

    @override(Model, 'ebay_')
    def write(self, *args, **kwargs):
        print 'I am in the write overwrited 3', self._name
        return Model.ebay_write(self, *args, **kwargs)

    """
    def decorator(func):
        if not hasattr(class_to_extend, func.func_name):
            raise except_osv(_("Developper Error"),
                _("You can replace the method %s of the class %s. "
                "Indeed this method doesn't exist")%(func.func_name, class_to_extend))
        original_function_name = prefix + func.func_name
        if hasattr(class_to_extend, original_function_name):
            raise except_osv(_("Developper Error"),
                _("The method %s already exist. "
                "Please change the prefix name")%original_function_name)
        setattr(class_to_extend, original_function_name, getattr(class_to_extend, func.func_name))
        setattr(class_to_extend, func.func_name, func)
        return class_to_extend
    return decorator


class ExternalSession(object):
    def __init__(self, referential, sync_from_object=None):
        """External Session in an object to store the information about a connection with an
        external system, like Magento, Prestashop, Ebay, ftp....
        This class have for fields
        - referential_id : a many2one related to the referential used for this connection
        - sync_from_object : a many2one related to the object that launch the synchronization
           for example if you import the product from the shop, the shop will be store in this field1
        - debug : boolean to active or not the debug
        - connection : the connection object of the external system
        - tmp : a temporary dict to store data
        """
        self.referential_id = referential
        self.sync_from_object = sync_from_object or referential
        self.debug = referential.debug
        self.logger = logging.getLogger(referential.name)
        self.connection = referential.external_connection(debug=self.debug, logger = self.logger)
        self.tmp = {}

    def is_type(self, referential_type):
        return self.referential_id.type_id.name.lower() == referential_type.lower()

    def is_categ(self, referential_category):
        return self.referential_id.categ_id.name.lower() == referential_category.lower()

# XXX unused ?
#TODO think about the generic method to use
class Resource(object):
    """Resource class in a container for using other class like objectify as a dictionnary
    The implemented dict fonctionality are "get", "__getitem__", "keys"
    The original object is store in the data field

    Example :
      resource = Resource(objectify_resource)
      my_keys = resource.keys()
      one_key = my_keys[0]
      my_item = resource[one_key]
      my_item = resource.get(one_key)
    """
    def __init__(self, data):
        self.data = data

    def get(self, key):
        if isinstance(self.data, objectify.ObjectifiedElement):
            if key in self.data.__dict__:
                result = self.data.__dict__.get(key)
            else:
                return None
            if hasattr(result, 'pyval'):
                return result.pyval
            else:
                return Resource(result)

    def __getitem__(self, key):
        if isinstance(self.data, objectify.ObjectifiedElement):
            return self.get(key)

    def keys(self):
        if isinstance(self.data, objectify.ObjectifiedElement):
            return self.data.__dict__.keys()



########################################################################################################################
#
#                                             BASIC FEATURES
#
########################################################################################################################

@extend(Model)
def read_w_order(self, cr, uid, ids, fields_to_read=None, context=None, load='_classic_read'):
    """Read records with given ids with the given fields and return it respecting the order of the ids
    This is very usefull for synchronizing data in a special order with an external system

    :param list ids: list of the ids of the records to read
    :param list fields_to_read: optional list of field names to return (default: all fields would be returned)
    :param dict context: context arguments, like lang, time zone
    :rtype: [{‘name_of_the_field’: value, ...}, ...]
    :return: ordered list of dictionaries((dictionary per record asked)) with requested field values
    """
    res = self.read(cr, uid, ids, fields_to_read, context, load)
    resultat = []
    for id in ids:
        resultat += [x for x in res if x['id'] == id]
    return resultat

@extend(Model)
def browse_w_order(self, cr, uid, ids, context=None, list_class=None, fields_process={}):
    """Fetch records as objects and return it respecting the order of the ids
    This is very usefull for synchronizing data in a special order with an external system

    :param list ids: id or list of ids.
    :param dict context: context arguments, like lang, time zone
    :rtype: list of objects requested
    :return: ordered list of object
    """
    res = self.browse(cr, uid, ids, context, list_class, fields_process)
    resultat = []
    for id in ids:
        resultat += [x for x in res if x.id == id]
    return resultat

@extend(Model)
def prefixed_id(self, id):
    """Return the prefixed_id for an id given
    :param str or int id: external id
    :rtype str
    :return the prefixed id
    """
    #The reason why we don't just use the external id and put the model as the prefix
    #is to avoid unique ir_model_data#name per module constraint violation.
    return self._name.replace('.', '_') + '/' + str(id)

@extend(Model)
def id_from_prefixed_id(self, prefixed_id):
    """Return the external id extracted from an prefixed_id

    :param str prefixed_id: prefixed_id to process
    :rtype int/str
    :return the id extracted
    """
    res = prefixed_id.split(self._name.replace('.', '_') + '/')[1]
    if res.isdigit():
        return int(res)
    else:
        return res

@extend(Model)
def get_all_extid_from_referential(self, cr, uid, referential_id, context=None):
    """Returns the external ids of the ressource which have an ext_id in the referential
    :param int referential_id : id of the external referential
    :rtype: list
    :return: the list of all of the external_ids from the referential specified
    """
    ir_model_data_obj = self.pool.get('ir.model.data')
    model_data_ids = ir_model_data_obj.search(cr, uid, [('model', '=', self._name), ('referential_id', '=', referential_id)])
    #because OpenERP might keep ir_model_data (is it a bug?) for deleted records, we check if record exists:
    oeid_to_extid = {}
    for data in ir_model_data_obj.read(cr, uid, model_data_ids, ['res_id', 'name'], context=context):
        oeid_to_extid[data['res_id']] = self.id_from_prefixed_id(data['name'])
    if not oeid_to_extid:
        return []
    return [int(oeid_to_extid[oe_id]) for oe_id in self.exists(cr, uid, oeid_to_extid.keys(), context=context)]

@extend(Model)
def get_all_oeid_from_referential(self, cr, uid, referential_id, context=None):
    """Returns the openerp ids of the ressource which have an ext_id in the referential
    :param int referential_id : id of the external referential
    :rtype: list
    :return: the list of all of the openerp ids which have an ext_id in the referential specified
    """

    ir_model_data_obj = self.pool.get('ir.model.data')
    model_data_ids = ir_model_data_obj.search(cr, uid, [('model', '=', self._name), ('referential_id', '=', referential_id)])
    #because OpenERP might keep ir_model_data (is it a bug?) for deleted records, we check if record exists:
    claimed_oe_ids = [x['res_id'] for x in ir_model_data_obj.read(cr, uid, model_data_ids, ['res_id'], context=context)]
    return claimed_oe_ids and self.exists(cr, uid, claimed_oe_ids, context=context) or []

@extend(Model)
def get_or_create_extid(self, cr, uid, external_session, openerp_id, context=None):
    """Returns the external id of a resource by its OpenERP id.
    If not external id have been found, the resource will be automatically exported
    :param ExternalSession external_session : External_session that contain all params of connection
    :param int openerp_id : openerp id of the resource
    :return: the external id of the resource
    :rtype: int
    """
    res = self.get_extid(cr, uid, openerp_id, external_session.referential_id.id, context=context)
    if res is not False:
        return res
    else:
        return self._export_one_resource(cr, uid, external_session, openerp_id, context=context)

@extend(Model)
def get_extid(self, cr, uid, openerp_id, referential_id, context=None):
    """Returns the external id of a resource by its OpenERP id.
    :param int openerp_id : openerp id of the resource
    :param int referential_id : referential id
    :rtype: int
    """
    if isinstance(openerp_id, list):
        openerp_id = openerp_id[0]
    model_data_ids = self.pool.get('ir.model.data').search(cr, uid, [('model', '=', self._name), ('res_id', '=', openerp_id), ('referential_id', '=', referential_id)])
    if model_data_ids and len(model_data_ids) > 0:
        prefixed_id = self.pool.get('ir.model.data').read(cr, uid, model_data_ids[0], ['name'])['name']
        ext_id = self.id_from_prefixed_id(prefixed_id)
        return ext_id
    return False

#TODO Deprecated remove for V7 version
@extend(Model)
def oeid_to_existing_extid(self, cr, uid, referential_id, openerp_id, context=None):
    """Returns the external id of a resource by its OpenERP id.
    Returns False if the resource id does not exists."""
    return self.get_extid(cr, uid, openerp_id, referential_id, context=context)

Model.oeid_to_extid = Model.get_or_create_extid
############## END OF DEPRECATED


@extend(Model)
def _get_expected_oeid(self, cr, uid, external_id, referential_id, context=None):
    """Returns the id of the entry in ir.model.data and the expected id of the resource in the current model
    Warning the expected_oe_id may not exists in the model, that's the res_id registered in ir.model.data

    :param int/str external_id: id in the external referential
    :param int referential_id: id of the external referential
    :return: tuple of (ir.model.data entry id, expected resource id in the current model)
    :rtype: tuple
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

@extend(Model)
def get_oeid(self, cr, uid, external_id, referential_id, context=None):
    """Returns the OpenERP id of a resource by its external id.
    Returns False if the resource does not exist.

    :param int/str external_id : external id of the resource
    :param int referential_id : referential id
    :return: the openerp id of the resource or False if not exist
    :rtype: int
       """
    if external_id:
        ir_model_data_id, expected_oe_id = self._get_expected_oeid\
            (cr, uid, external_id, referential_id, context=context)
        # Note: OpenERP cleans up ir_model_data which res_id records have been deleted
        # only at server update because that would be a perf penalty, we returns the res_id only if
        # really existing and we delete the ir_model_data unused
        if expected_oe_id and self.exists(cr, uid, expected_oe_id, context=context):
            return expected_oe_id
    return False

@extend(Model)
def get_or_create_oeid(self, cr, uid, external_session, external_id, context=None):
    """Returns the OpenERP ID of a resource by its external id.
    Creates the resource from the external connection if the resource does not exist.

    :param ExternalSession external_session : External_session that contain all params of connection
    :param int/str external_id : external id of the resource
    :return: the openerp id of the resource
    :rtype: int
    """
    if external_id:
        existing_id = self.get_oeid(cr, uid, external_id, external_session.referential_id.id, context=context)
        if existing_id:
            return existing_id
        return self._import_one_resource(cr, uid, external_session, external_id, context=context)
    return False

#TODO Deprecated remove for V7 version
@extend(Model)
def extid_to_existing_oeid(self, cr, uid, referential_id, external_id, context=None):
    """Returns the OpenERP id of a resource by its external id.
       Returns False if the resource does not exist."""
    res = self.get_oeid(cr, uid, external_id, referential_id, context=context)
    return res

Model.extid_to_oeid = Model.get_or_create_oeid
############## END OF DEPRECATED


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


# XXX a degager
@extend(Model)
def _get_filter(self, cr, uid, external_session, step, previous_filter=None, context=None):
    """Abstract function that return the filter
    Can be overwriten in your module

    :param ExternalSession external_session : External_session that contain all params of connection
    :param int step: Step the of the import, 100 meant you will import data per 100
    :param dict previous_filter: the previous filter
    :rtype: dict
    :return: dictionary with a filter
    """
    return None

# XXX a degager
@extend(Model)
def _get_external_resource_ids(self, cr, uid, external_session, resource_filter=None, mapping=None, context=None):
    """Abstract function that return the external resource ids
    Can be overwriten in your module

    :param ExternalSession external_session : External_session that contain all params of connection
    :param dict resource_filter: the filter to apply to the external search method
    :param dict mapping: dictionnary of mapping, the key is the mapping id
    :rtype: list
    :return: a list of external_id
    """
    raise except_osv(_("Not Implemented"), _("The method _get_external_resource_ids is not implemented in abstract base module!"))

# XXX a degager
@extend(Model)
def _get_default_import_values(self, cr, uid, external_session, mapping_id=None, defaults=None, context=None):
    """Abstract function that return the default value for on object
    Can be overwriten in your module

    :param ExternalSession external_session : External_session that contain all params of connection
    :param int mapping_id: id of the mapping
    :rtype: dict
    :return: a dictionnary of default values
    """
    return defaults

# XXX a degager
@extend(Model)
def _get_import_step(self, cr, uid, external_session, context=None):
    """Abstract function that return the step for importing data
    Can be overwriten in your module

    :param ExternalSession external_session : External_session that contain all params of connection
    :rtype: int
    :return: a integer that corespond to the limit of object to import
    """
    return 100

# XXX a degager
@extend(Model)
def _get_external_resources(self, cr, uid, external_session, external_id=None, resource_filter=None, mapping=None, fields=None, context=None):
    """Abstract function that return the external resource
    Can be overwriten in your module

    :param ExternalSession external_session : External_session that contain all params of connection
    :param int external_id : resource external id to import
    :param dict resource_filter: the filter to apply to the external search method
    :param dict mapping: dictionnary of mapping, the key is the openerp object's name
    :param list fields: list of field to read
    :rtype: list
    :return: a list of dict that contain resource information
    """
    mapping, mapping_id = self._init_mapping(cr, uid,
                                             external_session.referential_id.id,
                                             mapping=mapping,
                                             context=context)
    if not resource_filter:
        resource_filter = {}
    if external_id:
        filter_key = mapping[mapping_id]['key_for_external_id']
        resource_filter[filter_key] = external_id

    external_get_meth = getattr(external_session.connection,
                                mapping[mapping_id]['external_get_method'])
    return external_get_meth(mapping[mapping_id]['external_resource_name'], resource_filter)

# XXX a degager
@extend(Model)
def _get_mapping_id(self, cr, uid, referential_id, context=None):
    """Function that return the mapping id for the corresponding object

    :param int referential_id: the referential id
    :rtype integer
    :return the id of the mapping
    """
    mapping_id = self.pool.get('external.mapping').search(cr, uid, [('model', '=', self._name),
                                                                    ('referential_id', '=', referential_id)],
                                                          context=context)
    return mapping_id and mapping_id[0] or False

# XXX a degager
@extend(Model)
def _init_mapping(self, cr, uid, referential_id, convertion_type='from_external_to_openerp',
                  mapping_line_filter_ids=None, mapping=None, mapping_id=None, context=None):
    """Function to initialise mapping
    :param int referential_id: the referential id
    :param str convertion_type: the type of convertion 'from_external_to_openerp' or 'from_openerp_to_external'
    :param list mapping_line_filter_ids: list of mappin line allowed to used
    :param dict mapping: dict of mapping already loaded
    :param int mapping_id: mapping id
    :rtype int
    :return the id of the mapping
    """
    if not mapping:
        mapping={}
    if not mapping_id:
        mapping_id = self._get_mapping_id(cr, uid, referential_id, context=context)
    if not mapping.get(mapping_id):
        mapping[mapping_id] = self._get_mapping(cr, uid, referential_id,
                                                convertion_type=convertion_type,
                                                mapping_line_filter_ids=mapping_line_filter_ids,
                                                mapping_id=mapping_id,
                                                context=context)
    return mapping, mapping_id

# XXX a degager
@extend(Model)
def _get_mapping(self, cr, uid, referential_id, convertion_type='from_external_to_openerp',
                 mapping_line_filter_ids=None, mapping_id=None, context=None):
    """Function that return the mapping line for the corresponding object

    :param  int referential_id: the referential id
    :param str convertion_type: the type of convertion 'from_external_to_openerp' or 'from_openerp_to_external'
    :param list mapping_line_filter_ids: list of mappin line allowed to used
    :param int mapping_id: mapping id
    :rtype: dict
    :return: dictionary with the key "mapping_lines" and "key_for_external_id"
    """
    if not mapping_id:
        mapping_id = self._get_mapping_id(cr, uid, referential_id, context=context)
    if not mapping_id:
        raise except_osv(_('External Import Error'),
                         _("The object %s doesn't have an external mapping" % self._name))
    else:
        #If a mapping exists for current model, search for mapping lines

        mapping_type = convertion_type == 'from_external_to_openerp' and 'in' or 'out'
        mapping_line_filter = [('mapping_id', '=', mapping_id),
                            ('type', 'in', ['in_out', mapping_type])]
        if mapping_line_filter_ids:
            mapping_line_filter += ['|',
                                    ('id', 'in', mapping_line_filter_ids),
                                    ('evaluation_type', '=', 'sub-mapping')]
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


# XXX move this method to the referential class
# add specific implementaiton in e-commerce-addons for shops (in base_sale_multichannel)
@extend(Model)
def import_resources(self, cr, uid, ids, resource_name, method="search_then_read", context=None):
    """Abstract function to import resources from a shop / a referential...

    :param list ids: list of id
    :param str ressource_name: the resource name to import
    :param str method: method used for importing the resource (search_then_read,
                            search_then_read_no_loop, search_read, search_read_no_loop )
    :rtype: dict
    :return: dictionary with the key "create_ids" and "write_ids" which containt the id created/written
    """
    if context is None: context={}
    result = {"create_ids" : [], "write_ids" : []}
    for browse_record in self.browse(cr, uid, ids, context=context):
        if browse_record._name == 'external.referential':
            external_session = ExternalSession(browse_record, browse_record)
        else:
            if hasattr(browse_record, 'referential_id'):
                context['%s_id'%browse_record._name.replace('.', '_')] = browse_record.id
                external_session = ExternalSession(browse_record.referential_id, browse_record)
            else:
                raise except_osv(_("Not Implemented"),
                                 _("The field referential_id doesn't exist on the object %s. Reporting system can not be used") % (browse_record._name,))
        defaults = self.pool.get(resource_name)._get_default_import_values(cr, uid, external_session, context=context)
        res = self.pool.get(resource_name)._import_resources(cr, uid, external_session, defaults, method=method, context=context)
        for key in result:
            result[key].append(res.get(key, []))
    return result


# XXX move this to the connector class
@extend(Model)
def _import_resources(self, cr, uid, external_session, defaults=None, method="search_then_read", context=None):
    """Abstract function to import resources form a specific object (like shop, referential...)

    :param ExternalSession external_session : External_session that contain all params of connection
    :param dict defaults: default value for the resource to create
    :param str method: method used for importing the resource (
                        search_then_read,
                        search_then_read_no_loop,
                        search_read,
                        search_read_no_loop )
    :rtype: dict
    :return: dictionary with the key "create_ids" and "write_ids" which containt the id created/written
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
                        result[key] += res.get(key, [])
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
                    result[key] += res.get(key, [])
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
                    result[key] += res.get(key, [])
        elif method == 'search_read_no_loop':
            #Magento API do not support step import so we can not use a loop
            resource_filter = self._get_filter(cr, uid, external_session, step, previous_filter=resource_filter, context=context)
            #TODO import only the field needed to improve speed import ;)
            resources = self._get_external_resources(cr, uid, external_session, resource_filter=resource_filter, mapping=mapping, fields=None, context=context)
            if not isinstance(resources, list):
                resources = [resources]
            res = self._record_external_resources(cr, uid, external_session, resources, defaults=defaults, mapping=mapping, mapping_id=mapping_id, context=context)
            for key in result:
                result[key] += res.get(key, [])
    return result

# XXX a degager
@extend(Model)
def _import_one_resource(self, cr, uid, external_session, external_id, context=None):
    """Abstract function to import one resource

    :param ExternalSession external_session : External_session that contain all params of connection
    :param int external_id : resource external id to import
    :return: the openerp id of the resource imported
    :rtype: int
    """
    resources = self._get_external_resources(cr, uid, external_session, external_id, context=context)
    defaults = self._get_default_import_values(cr, uid, external_session, context=context)
    if isinstance(resources, list):
        res = self._record_external_resources(cr, uid, external_session, resources, defaults=defaults, context=context)
        id = res['write_ids'][0] if res.get('write_ids') else res['create_ids'][0]
    else:
        res = self._record_one_external_resource(cr, uid, external_session, resources, defaults=defaults, context=context)
        if res.get('write_id'):
            id = res.get('write_id')
        else:
            id = res.get('create_id')
    return id

# XXX a degager
@extend(Model)
def _record_external_resources(self, cr, uid, external_session, resources, defaults=None, mapping=None, mapping_id=None, context=None):
    """Abstract function to record external resources (this will convert the data and create/update the object in openerp)

    :param ExternalSession external_session : External_session that contain all params of connection
    :param list resource: list of resource to import
    :param dict defaults: default value for the resource to create
    :param dict mapping: dictionnary of mapping, the key is the mapping id
    :param int mapping_id: mapping id
    :rtype: dict
    :return: dictionary with the key "create_ids" and "write_ids" which containt the id created/written
    """
    if context is None: context = {}
    result = {'write_ids': [], 'create_ids': []}
    mapping, mapping_id = self._init_mapping(cr, uid, external_session.referential_id.id, mapping=mapping, mapping_id=mapping_id, context=context)
    if mapping[mapping_id]['key_for_external_id']:
        context['external_id_key_for_report'] = mapping[mapping_id]['key_for_external_id']
    else:
        for field in mapping[mapping_id]['mapping_lines']:
            if field['alternative_key']:
                context['external_id_key_for_report'] = field['external_field']
                break
    for resource in resources:
        res = self._record_one_external_resource(cr, uid, external_session, resource, defaults=defaults, mapping=mapping, mapping_id=mapping_id, context=context)
        if res:
            if 'create_id' in res:
                result['create_ids'].append(res['create_id'])
            if 'write_id'in res:
                result['write_ids'].append(res['write_id'])
    return result

# XXX a degager
@extend(Model)
def _record_one_external_resource(self, cr, uid, external_session, resource, defaults=None, mapping=None, mapping_id=None, context=None):
    """Used in _record_external_resources
    The resource will converted into OpenERP data by using the function _transform_external_resources
    And then created or updated, and an external id will be added into the table ir.model.data

    :param ExternalSession external_session : External_session that contain all params of connection
    :param dict resource: resource to convert into OpenERP data
    :param dict defaults: default values
    :param dict mapping: dictionnary of mapping, the key is the mapping id
    :param int mapping_id: mapping id
    :rtype: dict
    :return: dictionary with the key "create_id" and "write_id" which containt the id created/written
    """
    mapping, mapping_id = self._init_mapping(cr, uid, external_session.referential_id.id, mapping=mapping, mapping_id=mapping_id, context=context)
    written = created = False
    vals = self._transform_one_resource(cr, uid, external_session, 'from_external_to_openerp', resource, mapping=mapping, mapping_id=mapping_id, defaults=defaults, context=context)
    if not vals:
        # for example in the case of an update on existing resource if update is not wanted vals will be {}
        return {}
    referential_id = external_session.referential_id.id
    external_id = vals.get('external_id')
    external_id_ok = not (external_id is None or external_id is False)
    alternative_keys = mapping[mapping_id]['alternative_keys']
    existing_rec_id = False
    existing_ir_model_data_id = False
    if external_id_ok:
        del vals['external_id']
    existing_ir_model_data_id, existing_rec_id = self._get_oeid_from_extid_or_alternative_keys\
            (cr, uid, vals, external_id, referential_id, alternative_keys, context=context)

    if not (external_id_ok or alternative_keys):
        external_session.logger.warning(_("The object imported need an external_id, maybe the mapping doesn't exist for the object : %s" %self._name))

    if existing_rec_id:
        if not self._name in context.get('do_not_update', []):
            if self.oe_update(cr, uid, external_session, existing_rec_id, vals, resource, defaults=defaults, context=context):
                written = True
    else:
        existing_rec_id = self.oe_create(cr, uid,  external_session, vals, resource, defaults, context=context)
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

# XXX a degager
@extend(Model)
def oe_update(self, cr, uid, external_session, existing_rec_id, vals, resource, defaults, context=None):
    """Update an existing resource in OpenERP

    :param ExternalSession external_session : External_session that contain all params of connection
    :param int existing_rec_id: openerp id to update
    :param dict vals: vals to write
    :param dict resource: resource to convert into OpenERP data
    :param dict defaults: default values
    :rtype boolean
    :return: True
    """
    if context is None: context={}
    context['referential_id'] = external_session.referential_id.id #did it's needed somewhere?
    return self.write(cr, uid, existing_rec_id, vals, context)

# XXX a degager
@extend(Model)
def oe_create(self, cr, uid, external_session, vals, resource, defaults, context=None):
    """Create an new resource in OpenERP

    :param ExternalSession external_session : External_session that contain all params of connection
    :param dict vals: vals to create
    :param dict resource: resource to convert into OpenERP data
    :param dict defaults: default values
    :rtype int
    :return: the id of the resource created
    """
    if context is None: context={}
    context['referential_id'] = external_session.referential_id.id  #did it's needed somewhere?
    return self.create(cr, uid, vals, context)

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

@extend(Model)
def _get_export_step(self, cr, uid, external_session, context=None):
    """Abstract function that return the step for importing data
    Can be overwriten in your module

    :param ExternalSession external_session : External_session that contain all params of connection
    :rtype: int
    :return: a integer that corespond to the limit of object to import
    """
    return 10

@extend(Model)
def _get_default_export_values(self, cr, uid, external_session, mapping_id=None, defaults=None, context=None):
    """Abstract function that return the default value for on object
    Can be overwriten in your module

    :param ExternalSession external_session : External_session that contain all params of connection
    :param int mapping_id: mapping id
    :param dict defaults: default values
    :rtype: dict
    :return: a dictionnary of default values
    """
    return defaults

@extend(Model)
def _get_last_exported_date(self, cr, uid, external_session, context=None):
    """Abstract function that return the last export date for on object
    Can be overwriten in your module

    :param ExternalSession external_session : External_session that contain all params of connection
    :rtype: str
    :return: the last export date or False
    """
    return False

@extend(Model)
def _set_last_exported_date(self, cr, uid, external_session, date, context=None):
    """Abstract function that update the last exported date
    Can be overwriten in your module

    :param ExternalSession external_session : External_session that contain all params of connection
    :param date : date
    :rtype: boolean
    :return: True
    """
    return True

#For now it's just support 1 level of inherit TODO make it recursive
@extend(Model)
def _get_query_and_params_for_ids_and_date(self, cr, uid, external_session, ids=None, last_exported_date=None, context=None):
    """Function that build the sql query for getting the ids and the udpate date of each record

    :param ExternalSession external_session : External_session that contain all params of connection
    :param list ids : if not empty the ids will be used in the sql request in order to filter the record
    :param str last_exported_date : last exported date
    :rtype: tuple
    :return: an tuple of query and params
    """
    object_table = self._table
    params = ()
    if not self._inherits:
        greatest = "GREATEST(%(object_table)s.write_date, %(object_table)s.create_date)"\
                        %{'object_table': object_table}

        query = """
            SELECT %(greatest)s as update_date, %(object_table)s.id as id, ir_model_data.res_id
                FROM %(object_table)s
            LEFT JOIN ir_model_data
                ON %(object_table)s.id = ir_model_data.res_id
                AND ir_model_data.model = '%(object_name)s'
                AND ir_model_data.module = 'extref/%(ref_name)s'
            """%{
                    'greatest': greatest,
                    'object_table': object_table,
                    'object_name': self._name,
                    'ref_name': external_session.referential_id.name,
            }
    else:
        inherits_object_table = self.pool.get(self._inherits.keys()[0])._table
        join_field = self._inherits[self._inherits.keys()[0]]

        greatest = """GREATEST(%(object_table)s.write_date, %(object_table)s.create_date,
                    %(inherits_object_table)s.write_date, %(inherits_object_table)s.create_date)""" \
                    %{'object_table': object_table, 'inherits_object_table': inherits_object_table}

        query = """
            select %(greatest)s as update_date, %(object_table)s.id as id, ir_model_data.res_id
                from %(object_table)s
                    join %(inherits_object_table)s on %(inherits_object_table)s.id = %(object_table)s.%(join_field)s
                    LEFT JOIN ir_model_data
                        ON %(object_table)s.id = ir_model_data.res_id
                        AND ir_model_data.model = '%(object_name)s'
                        AND ir_model_data.module = 'extref/%(ref_name)s'
            """ %{
                    'greatest': greatest,
                    'object_table': object_table,
                    'inherits_object_table': inherits_object_table,
                    'join_field': join_field,
                    'object_name': self._name,
                    'ref_name': external_session.referential_id.name,
                }
    if ids:
        query += " WHERE " + object_table + ".id in %s"
        params += (tuple(ids),)
    if last_exported_date:
        query += (ids and " AND (" or " WHERE (") + greatest + " > %s or ir_model_data.res_id is NULL)"
        params += (last_exported_date,)

    query += " order by update_date asc;"
    return query, params

@extend(Model)
def get_ids_and_update_date(self, cr, uid, external_session, ids=None, last_exported_date=None, context=None):
    """This function will return the list of ids and the update date of each record_dicts

    :param ExternalSession external_session : External_session that contain all params of connection
    :param list ids : if not empty the ids will be used in the sql request in order to filter the record
    :param str last_exported_date : last exported date
    :rtype: tuple
    :return: an tuple of ids and ids_2_dates (dict with key => 'id' and val => 'last_update_date')
    """
    if ids in [[], ()]:
        return [], {}
    query, params = self._get_query_and_params_for_ids_and_date(cr, uid, external_session, ids=ids, last_exported_date=last_exported_date, context=context)
    cr.execute(query, params)
    read = cr.dictfetchall()
    ids = []
    ids_2_dates = {}
    for data in read:
        ids.append(data['id'])
        ids_2_dates[data['id']] = data['update_date']
    return ids, ids_2_dates


#Deprecated
@extend(Model)
def init_context_before_exporting_resource(self, cr, uid, external_session, object_id, resource_name, context=None):
    if self._name != 'external.referential' and 'referential_id' in self._columns.keys():
        context['%s_id'%self._name.replace('.', '_')] = object_id
    return context

@extend(Model)
def export_resources(self, cr, uid, ids, resource_name, context=None):
    """
    Abstract function to export resources from a shop / a referential...

    :param list ids: list of id
    :param string ressource_name: the resource name to import
    :return: True
    :rtype: boolean
    """
    for browse_record in self.browse(cr, uid, ids, context=context):
        if browse_record._name == 'external.referential':
            external_session = ExternalSession(browse_record, browse_record)
        else:
            if hasattr(browse_record, 'referential_id'):
                external_session = ExternalSession(browse_record.referential_id, browse_record)
            else:
                raise except_osv(_("Not Implemented"), _("The field referential_id doesn't exist on the object %s." %(browse_record._name,)))
        context = self.init_context_before_exporting_resource(cr, uid, external_session, browse_record.id, resource_name, context=context)
        self.pool.get(resource_name)._export_resources(cr, uid, external_session, context=context)
    return True


#TODO refactor update date,maybe it will be better to have an update date per resource
#TODO deal correctly with multi resource
@extend(Model)
def send_to_external(self, cr, uid, external_session, resources, mapping, mapping_id, update_date=None, context=None):
    """Generic method that send the resource to an external referential

    :param ExternalSession external_session : External_session that contain all params of connection
    :param list resources: list of resources to export
    :param dict mapping: dictionnary of mapping, the key is the mapping id
    :param date update_date: if not empty the update date will be write in the last update date of the objec
    :rtype: int/str
    :return: the external resource exported

    """
    resources_to_update = {}
    resources_to_create = {}
    for resource_id, resource in resources.items():
        ext_id = self.get_extid(cr, uid, resource_id, external_session.referential_id.id, context=context)
        if ext_id:
            for lang in resource:
                resource[lang]['ext_id'] = ext_id
            resources_to_update[resource_id] = resource
        else:
            resources_to_create[resource_id] = resource
    self.ext_update(cr, uid, external_session, resources_to_update, mapping, mapping_id, context=context)
    ext_create_ids = self.ext_create(cr, uid, external_session, resources_to_create, mapping, mapping_id, context=context)
    for rec_id, ext_id in ext_create_ids.items():
        self.create_external_id_vals(cr, uid, rec_id, ext_id, external_session.referential_id.id, context=context)
    if update_date and self._get_last_exported_date(cr, uid, external_session, context=context) < update_date:
        self._set_last_exported_date(cr, uid, external_session, update_date, context=context)
    return ext_id

@extend(Model)
def ext_create(self, cr, uid, external_session, resources, mapping=None, mapping_id=None, context=None):
    res = {}
    mapping, mapping_id = self._init_mapping(cr, uid, external_session.referential_id.id, mapping=mapping, mapping_id=mapping_id, context=context)
    for resource_id, resource in resources.items():
        # TODO support multilanguages. for now we only export the first one
        res[resource_id] = getattr(external_session.connection, mapping[mapping_id]['external_create_method'])(mapping[mapping_id]['external_resource_name'], resource[resource.keys()[0]])
    return res

@extend(Model)
def ext_update(self, cr, uid, external_session, resources, mapping=None, mapping_id=None, context=None):
    """Not Implemented here"""
    return False

@extend(Model)
def ext_unlink(self, cr, uid, ids, context=None):
    ir_model_obj = self.pool.get('ir.model.data')
    for object_id in ids:
        ir_model_ids = ir_model_obj.search(cr, uid, [('res_id','=',object_id),('model','=',self._name)])
        for ir_model in ir_model_obj.browse(cr, uid, ir_model_ids, context=context):
            ext_id = self.id_from_prefixed_id(ir_model.name)
            ref_id = ir_model.referential_id.id
            external_session = ExternalSession(ir_model.referential_id)
            mapping = self._get_mapping(cr, uid, ref_id)
            getattr(external_session.connection, mapping['external_delete_method'])(mapping['external_resource_name'], ext_id)
            #commit_now(ir_model.unlink())
            ir_model.unlink()
    return True

@extend(Model)
def get_lang_to_export(self, cr, uid, external_session, context=None):
    """Get the list of lang to export

    :param ExternalSession external_session : External_session that contain all params of connection
    :rtype: list
    return: the list of lang to export
    """

    if context is None:
        return []
    else:
        return context.get('lang_to_export') or [context.get('lang')]

@extend(Model)
def _export_resources(self, cr, uid, external_session, method="onebyone", context=None):
    """Export resource

    :param ExternalSession external_session : External_session that contain all params of connection
    :param str method: method to export data (for now only onebyone)
    :rtype: boolean
    return: True
    """
    external_session.logger.info("Start to export the ressource %s"%(self._name,))
    defaults = self._get_default_export_values(cr, uid, external_session, context=context)
    mapping, mapping_id = self._init_mapping(cr, uid, external_session.referential_id.id, convertion_type='from_openerp_to_external', context=context)
    last_exported_date = self._get_last_exported_date(cr, uid, external_session, context=context)
    external_session.logger.info("Retrieve the list of ids to export for the ressource %s"%(self._name))
    ids, ids_2_date = self.get_ids_and_update_date(cr, uid, external_session, last_exported_date=last_exported_date, context=context)
    external_session.logger.info("%s %s ressource will be exported"%((ids and len(ids) or 0), self._name))
    step = self._get_export_step(cr, uid, external_session, context=context)

    group_obj = self.pool.get('group.fields')
    group_ids = group_obj.search(cr, uid, [['model_id', '=', self._name]], context=context)
    if self._inherits:
        inherits_group_ids = group_obj.search(cr, uid, [['model_id', '=',self._inherits.keys()[0]]], context=context)
    else:
        inherits_group_ids=[]
    smart_export =  context.get('smart_export') and (group_ids or inherits_group_ids) and {'group_ids': group_ids, 'inherits_group_ids': inherits_group_ids}

    langs = self.get_lang_to_export(cr, uid, external_session, context=context)

    while ids:
        ids_to_process = ids[0:step]
        ids = ids[step:]
        external_session.logger.info("Start to read the ressource %s : %s"%(self._name, ids_to_process))
        resources = self._get_oe_resources(cr, uid, external_session, ids_to_process, langs=langs,
                                    smart_export=smart_export, last_exported_date=last_exported_date,
                                    mapping=mapping, mapping_id=mapping_id, context=context)
        if method == 'onebyone':
            for resource_id in ids_to_process:
                external_session.logger.info("Start to transform and send the ressource %s : %s"%(self._name, resource_id))
                self._transform_and_send_one_resource(cr, uid, external_session, resources[resource_id], resource_id, ids_2_date.get(resource_id), mapping, mapping_id, defaults=defaults, context=context)
        else:
            raise except_osv(_('Developper Error'), _('only method export onebyone is implemented in base_external_referentials'))
    #now = datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT)
    #self._set_last_exported_date(cr, uid, external_session, now, context=context)
    return True

@extend(Model)
def _transform_and_send_one_resource(self, cr, uid, external_session, resource, resource_id,
                            update_date, mapping, mapping_id, defaults=None, context=None):
    """Transform and send one resource
    The resource will converted into External format by using the function _transform_one_resource
    And then send to the external system using the method send_to_external

    :param ExternalSession external_session : External_session that contain all params of connection
    :param dict resource: resource to convert into OpenERP data
    :param int resource_id: openerp id of the resource to send
    :param str method: method to export data (for now only onebyone)
    :param dict mapping: dictionnary of mapping, the key is the mapping id
    :param int mapping_id: mapping id
    :param dict defaults: default values
    :rtype: str/int
    :return: the external id
    """
    for key_lang in resource:
        resource[key_lang] = self._transform_one_resource(cr, uid, external_session, 'from_openerp_to_external',
                                            resource[key_lang], mapping=mapping, mapping_id=mapping_id,
                                            defaults=defaults, context=context)
    return self.send_to_external(cr, uid, external_session, {resource_id : resource}, mapping, mapping_id, update_date, context=context)

@extend(Model)
def _export_one_resource(self, cr, uid, external_session, resource_id, context=None):
    """Export one resource
    Export an OpenERP resource into an external system

    :param ExternalSession external_session : External_session that contain all params of connection
    :param int resource_id: openerp id of the resource to send
    :rtype: str/int
    :return: the external id
    """
    defaults = self._get_default_export_values(cr, uid, external_session, context=context)
    mapping, mapping_id = self._init_mapping(cr, uid, external_session.referential_id.id, convertion_type='from_openerp_to_external', context=context)
    langs = self.get_lang_to_export(cr, uid, external_session, context=context)
    resource = self._get_oe_resources(cr, uid, external_session, [resource_id], langs=langs,
                                smart_export=False, last_exported_date=False,
                                mapping=mapping, mapping_id=mapping_id, context=context)[resource_id]
    return self._transform_and_send_one_resource(cr, uid, external_session, resource, resource_id,
                            False, mapping, mapping_id, defaults=defaults, context=context)


#TODO finish docstring

@extend(Model)
def get_translatable_fields(self, cr, uid, fields, context=None):
    #TODO make fields parameter optionnal
    def is_translatable(field):
        if self._columns.get(field):
            return self._columns[field].translate
        else:
            return self._inherit_fields[field][2].translate
    translatable_fields = []
    untranslatable_fields = []
    for field in fields:
        if is_translatable(field):
            translatable_fields.append(field)
        else:
            untranslatable_fields.append(field)
    return translatable_fields, untranslatable_fields

@extend(Model)
def multi_lang_read(self, cr, uid, external_session, ids, fields_to_read, langs, resources=None, use_multi_lang = True, context=None):
    if not resources:
        resources = {}
    translatable_fields, untranslatable_fields = self.get_translatable_fields(cr, uid, fields_to_read, context=context)
    lang_support = external_session.referential_id._lang_support
    if lang_support == 'fields_with_no_lang':
        langs.insert(0, 'no_lang')
    first=True
    fields = fields_to_read
    for lang in langs:
        ctx = context.copy()
        if lang == 'no_lang':
            fields = untranslatable_fields
        else:
            if not first and lang_support == 'fields_with_main_lang' or lang_support == 'fields_with_no_lang':
                fields = translatable_fields
            ctx['lang'] = lang

        if fields:
            for resource in self.read(cr, uid, ids, fields, context=ctx):
                if not resources.get(resource['id']): resources[resource['id']] = {}
                resources[resource['id']][lang] = resource
        first = False
    return resources

@extend(Model)
def full_read(self, cr, uid, external_session, ids, langs, resources, mapping=None, mapping_id=None, context=None):
    fields_to_read = self.get_field_to_export(cr, uid, ids, mapping, mapping_id, context=context)
    return self.multi_lang_read(cr, uid, external_session, ids, fields_to_read, langs, resources=resources, context=context)

@extend(Model)
def smart_read(self, cr, uid, external_session, ids, langs, resources, group_ids, inherits_group_ids, last_exported_date=None,
                                                                        mapping=None, mapping_id=None, context=None):
    if last_exported_date:
        search_filter = []
        if group_ids:
            if inherits_group_ids:
                search_filter = ['|', ['x_last_update', '>=', last_exported_date], ['%s.x_last_update'%self._inherits[self._inherits.keys()[0]], '>=', last_exported_date]]
        if inherits_group_ids:
		search_filter = [['%s.x_last_update'%self._inherits[self._inherits.keys()[0]], '>=', last_exported_date]]
        resource_ids_full_read = self.search(cr, uid, search_filter, context=context)
        resource_ids_partial_read = [id for id in ids if not id in resource_ids_full_read]
    else:
        resource_ids_full_read = ids
        resource_ids_partial_read = []

    resources = self.full_read(cr, uid, external_session, resource_ids_full_read, langs, resources, context=context)

    if resource_ids_partial_read:
        for group in self.pool.get('group.fields').browse(cr, uid, group_ids, context=context):
            resource_ids = self.search(cr, uid, [[group.column_name, '>=', last_exported_date],['id', 'in', resource_ids_partial_read]], context=context)
            fields_to_read = [field.name for field in group.field_ids]
            resources = self.multi_lang_read(cr, uid, external_session, resource_ids, fields_to_read, langs, resources=resources, context=context)
    return resources

@extend(Model)
def get_field_to_export(self, cr, uid, ids, mapping, mapping_id, context=None):
    return list(set(self._columns.keys() + self._inherit_fields.keys()))

@extend(Model)
def _get_oe_resources(self, cr, uid, external_session, ids, langs, smart_export=None,
                                            last_exported_date=None, mapping=None, mapping_id=None, context=None):
    resources = None
    if smart_export:
        resources = self.smart_read(cr, uid, external_session, ids, langs, resources, smart_export['group_ids'], smart_export['inherits_group_ids'],
                            last_exported_date=last_exported_date, mapping=mapping, mapping_id=mapping_id, context=context)
    else:
        resources = self.full_read(cr, uid, external_session, ids, langs, resources, mapping=mapping, mapping_id=mapping_id, context=context)
    return resources


# XXX rename me
@extend(Model)
def _get_oeid_from_extid_or_alternative_keys(self, cr, uid, vals, external_id, referential_id, alternative_keys, context=None):
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
    existing_ir_model_data_id = expected_res_id = False
    if not (external_id is None or external_id is False):
        existing_ir_model_data_id, expected_res_id = self._get_expected_oeid\
        (cr, uid, external_id, referential_id, context=context)

    if not expected_res_id and alternative_keys:
        domain = []
        if 'active' in self._columns.keys():
            domain = ['|', ('active', '=', False), ('active', '=', True)]
        for alternative_key in alternative_keys:
            if vals.get(alternative_key):
                exp = type(vals[alternative_key]) in (str, unicode) and "=ilike" or "="
                domain.append((alternative_key, exp, vals[alternative_key]))
        if domain:
            expected_res_id = self.search(cr, uid, domain, context=context)
            expected_res_id = expected_res_id and expected_res_id[0] or False
    return existing_ir_model_data_id, expected_res_id

# XXX move to connector or referential
@extend(Model)
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

# XXX move to connector or referential
@extend(Model)
def create_external_id_vals(self, cr, uid, existing_rec_id, external_id, referential_id, context=None):
    """
    Add the external id in the table ir_model_data
    :param id existing_rec_id: erp id object
    :param id external_id: external application id
    :param id referential_id: external id
    :rtype: int
    :return:
    """
    ir_model_data_vals = \
    self._prepare_external_id_vals(cr, uid, existing_rec_id,
                                   external_id, referential_id,
                                   context=context)
    return self.pool.get('ir.model.data').create(cr, uid, ir_model_data_vals, context=context)

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

@extend(Model)
def _transform_resources(self, cr, uid, external_session, convertion_type, resources, mapping=None, mapping_id=None,
                    mapping_line_filter_ids=None, parent_data=None, defaults=None, context=None):
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
        mapping, mapping_id = self._init_mapping(cr, uid, external_session.referential_id.id,
                                                 convertion_type=convertion_type,
                                                 mapping_line_filter_ids=mapping_line_filter_ids,
                                                 mapping=mapping,
                                                 mapping_id=mapping_id,
                                                 context=context)
        if mapping[mapping_id].get("mapping_lines"):
            for resource in resources:
                result.append(self._transform_one_resource(cr, uid, external_session, convertion_type, resource,
                                                            mapping, mapping_id, mapping_line_filter_ids, parent_data=parent_data,
                                                            previous_result=result, defaults=defaults, context=context))
    return result

@extend(Model)
def _transform_one_resource(self, cr, uid, external_session, convertion_type, resource, mapping=None, mapping_id=None,
                    mapping_line_filter_ids=None, parent_data=None, previous_result=None, defaults=None, context=None):
    """
    Used in _transform_external_resources in order to convert external row of data into OpenERP data

    @param referential_id: external referential id from where we import the resource
    @param resource: a dictionnary of data, an lxml.objectify object...
    @param mapping dict: dictionnary of mapping {'product.product' : {'mapping_lines' : [...], 'key_for_external_id':'...'}}
    @param previous_result: list of the previous line converted. This is not used here but it's necessary for playing on change on sale order line
    @param defaults: defaults value for the data imported
    @return: dictionary of converted data in OpenERP format
    """

    #Encapsulation of the resource if it not a dictionnary
    #So we can use the same method to read it
    if not isinstance(resource, dict):
        resource = Resource(resource)

    if context is None:
        context = {}
    if defaults is None:
        defaults = {}

    referential_id = external_session.referential_id.id
    mapping, mapping_id = self._init_mapping(cr, uid, referential_id,
                                             convertion_type=convertion_type,
                                             mapping_line_filter_ids=mapping_line_filter_ids,
                                             mapping=mapping,
                                             mapping_id=mapping_id,
                                             context=context)

    mapping_lines = mapping[mapping_id].get("mapping_lines")
    key_for_external_id = mapping[mapping_id].get("key_for_external_id")

    vals = {} #Dictionary for create record
    sub_mapping_list=[]
    for mapping_line in mapping_lines:
        if convertion_type == 'from_external_to_openerp':
            from_field = mapping_line['external_field']
            if not from_field and mapping_line['evaluation_type'] != 'function':
                from_field = "%s_%s" %(mapping_line['child_mapping_id'][1], mapping_line['child_mapping_id'][0])
            to_field = mapping_line['internal_field']
        elif convertion_type == 'from_openerp_to_external':
            from_field = mapping_line['internal_field']
            to_field = mapping_line['external_field']

        if mapping_line['evaluation_type'] == 'function' or from_field in resource.keys(): #function field should be always played as they can depend on every field
            field_value = resource.get(from_field)
            if mapping_line['evaluation_type'] == 'sub-mapping':
                sub_mapping_list.append(mapping_line)
            else:
                if mapping_line['evaluation_type'] == 'direct':
                    vals[to_field] = self._transform_field(cr, uid, external_session,
                                                           convertion_type,
                                                           field_value,
                                                           mapping_line,
                                                           context=context)
                else:
                    #Build the space for expr
                    #Seb : removing ifield can be great ?
                    space = {'self': self,
                             'cr': cr,
                             'uid': uid,
                             'external_session': external_session,
                             'resource': resource,
                             'data': resource, #only for compatibility with the old version => deprecated
                             'parent_resource': parent_data, #TODO rename parent_data to parent_resource
                             'referential_id': external_session.referential_id.id,
                             'defaults': defaults,
                             'context': context,
                             'ifield': self._transform_field(cr, uid, external_session, convertion_type,
                                                             field_value, mapping_line, context=context),
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
                        #del(space['__builtins__'])
                        if config['debug_mode']: raise
                        raise MappingError(e, mapping_line['name'], self._name)

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
    ext_id = False
    if convertion_type == 'from_external_to_openerp' and key_for_external_id and resource.get(key_for_external_id):
        ext_id = resource[key_for_external_id]
        if isinstance(ext_id, str):
            ext_id = ext_id.isdigit() and int(ext_id) or ext_id
        vals.update({'external_id': ext_id})
    if self._name in context.get('do_not_update', []):
        # if the update of the object is not wanted, we skipped the
        # sub_mapping update also. In the function
        # _transform_one_resource, the creation will also be skipped.
        alternative_keys = mapping[mapping_id]['alternative_keys']
        existing_ir_model_data_id, existing_rec_id = self._get_oeid_from_extid_or_alternative_keys\
            (cr, uid, vals, ext_id, referential_id, alternative_keys, context=context)
        if existing_rec_id:
            return {}
    vals = self._merge_with_default_values(cr, uid, external_session, resource, vals, sub_mapping_list, defaults=defaults, context=context)
    vals = self._transform_sub_mapping(cr, uid, external_session,
                                       convertion_type, resource, vals, sub_mapping_list,
                                       mapping, mapping_id,
                                       mapping_line_filter_ids=mapping_line_filter_ids,
                                       defaults=defaults,
                                       context=context)

    return vals

@extend(Model)
def _transform_field(self, cr, uid, external_session, convertion_type, field_value, mapping_line, context=None):
    field = False
    external_type = mapping_line['external_type']
    internal_type = mapping_line['internal_type']
    internal_field = mapping_line['internal_field']
    if not (field_value is False or field_value is None):
        if internal_type == 'many2one' and mapping_line['evaluation_type']=='direct':
            if external_type not in ['int', 'unicode']:
                raise except_osv(_('User Error'),
                                 _('Wrong external type for mapping %s. One2Many object must have for external type string or integer') % (mapping_line['name'],))
            if self._columns.get(internal_field):
                related_obj_name = self._columns[internal_field]._obj
            else:
                related_obj_name = self._inherit_fields[internal_field][2]._obj
            related_obj = self.pool.get(related_obj_name)
            if convertion_type == 'from_external_to_openerp':
                if external_type == 'unicode':
                    #TODO it can be great if we can search on other field
                    related_obj.search(cr, uid, [(related_obj._rec_name, '=', field_value)], context=context)
                else:
                    return related_obj.get_or_create_oeid(cr, uid, external_session, field_value, context=context)
            else:
                if external_type == 'unicode':
                    #TODO it can be great if we can return on other field and not only the name
                    return field_value[1]
                else:
                    return related_obj.get_or_create_extid(cr, uid,external_session, field_value[0], context=context)

        elif external_type == "datetime":
            if not field_value:
                field_value = False
            else:
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
                    return datetime_value.strftime(datetime_format)

        elif external_type == 'list' and isinstance(field_value, (str, unicode)):
            # external data sometimes returns ',1,2,3' for a list...
            if field_value:
                casted_field = eval(field_value.strip(','))
            else:
                casted_field= []
            # For a list, external data may returns something like '1,2,3' but also '1' if only
            # one item has been selected. So if the casted field is not iterable, we put it in a tuple: (1,)
            if not hasattr(casted_field, '__iter__'):
                casted_field = (casted_field,)
            field = list(casted_field)
        elif external_type == 'url' and internal_type == "binary":
            (filename, header) = urllib.urlretrieve(field_value)
            try:
                f = open(filename , 'rb')
                data = f.read()
            finally:
                f.close()
            return base64.encodestring(data)
        else:
            if external_type == 'float' and isinstance(field_value, (str, unicode)):
                field_value = field_value.replace(',','.')
                if not field_value:
                    field_value = 0
            field = eval(external_type)(field_value)
    if field in ['None', 'False']:
        field = False

    #Set correct empty value for each type
    if field is False or field is None:
        empty_value = {
            'integer': 0,
            'unicode': '',
            'char': '',
            'date': False,
            'int': 0,
            'float': 0,
            'list': [],
            'dict': {},
            'boolean': False,
            'many2one': False,
            'one2many': [],
            'many2many': [],
            # external types
            'text': '',
            'textarea': '',
            'selection': 0,
            'multiselect': [],
        }
        if convertion_type == 'from_external_to_openerp':
            empty_value['datetime'] = False
        else:
            empty_value['datetime'] = ''
        if internal_type and convertion_type == 'from_external_to_openerp':
            field = empty_value[internal_type]
        elif external_type:
            # if the type is not specified in empty_value,
            # then we consider it will be False, if it
            # should not for an external_type, please add it
            # in empty_value
            field = empty_value.get(external_type, False)

    return field

@extend(Model)
def _merge_with_default_values(self, cr, uid, external_session, ressource, vals, sub_mapping_list, defaults=None, context=None):
    """
    Used in _transform_one_external_resource in order to merge the
    defaults values, some params are useless here but need in
    base_sale_multichannels to play the on_change

    @param sub_mapping_list: list of sub-mapping to apply
    @param external_data: list of data to convert into OpenERP data
    @param referential_id: external referential id from where we import the resource
    @param vals: dictionnary of value previously converted
    @param defauls: defaults value for the data imported
    @return: dictionary of converted data in OpenERP format
    """
    if not defaults: return vals
    for key in defaults:
        if not key in vals:
            vals[key] = defaults[key]
    return vals

@extend(Model)
def _transform_sub_mapping(self, cr, uid, external_session, convertion_type, resource, vals, sub_mapping_list,
                           mapping, mapping_id, mapping_line_filter_ids=None, defaults=None, context=None):
    """
    Used in _transform_one_external_resource in order to call the sub mapping

    @param sub_mapping_list: list of sub-mapping to apply
    @param resource: resource encapsulated in the object Resource or a dictionnary
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
        sub_mapping_id = sub_mapping['child_mapping_id'][0]
        if convertion_type == 'from_external_to_openerp':
            from_field = sub_mapping['external_field']
            if not from_field:
                from_field = "%s_%s" %(sub_object_name, sub_mapping_id)
            to_field = sub_mapping['internal_field']

        elif convertion_type == 'from_openerp_to_external':
            from_field = sub_mapping['internal_field']
            to_field = sub_mapping['external_field'] or 'hidden_field_to_split_%s'%from_field # if the field doesn't have any name we assume at that we will split it

        field_value = resource[from_field]
        sub_mapping_obj = self.pool.get(sub_object_name)
        sub_mapping_defaults = sub_mapping_obj._get_default_import_values(cr, uid, external_session, sub_mapping_id, defaults.get(to_field), context=context)

        if field_value:
            transform_args = [cr, uid, external_session, convertion_type, field_value]
            transform_kwargs = {
                'defaults': sub_mapping_defaults,
                'mapping': mapping,
                'mapping_id': sub_mapping_id,
                'mapping_line_filter_ids': mapping_line_filter_ids,
                'parent_data': vals,
                'context': context,
            }

            if sub_mapping['internal_type'] in ['one2many', 'many2many']:
                if not isinstance(field_value, list):
                    transform_args[4] = [field_value]
                if not to_field in vals:
                    vals[to_field] = []
                if convertion_type == 'from_external_to_openerp':
                    lines = sub_mapping_obj._transform_resources(*transform_args, **transform_kwargs)
                else:
                    mapping, sub_mapping_id = self._init_mapping(cr, uid, external_session.referential_id.id, \
                                                                    convertion_type=convertion_type,
                                                                    mapping=mapping,
                                                                    mapping_id=sub_mapping_id,
                                                                    context=context)
                    field_to_read = [x['internal_field'] for x in mapping[sub_mapping_id]['mapping_lines']]
                    sub_resources = sub_mapping_obj.read(cr, uid, field_value, field_to_read, context=context)
                    transform_args[4] = sub_resources
                    lines = sub_mapping_obj._transform_resources(*transform_args, **transform_kwargs)
                for line in lines:
                    if 'external_id' in line:
                        del line['external_id']
                    if convertion_type == 'from_external_to_openerp':
                        if sub_mapping['internal_type'] == 'one2many':
                            #TODO refactor to search the id and alternative keys before the update
                            external_id = vals.get('external_id')
                            alternative_keys = mapping[mapping_id]['alternative_keys']
                            #search id of the parent
                            existing_ir_model_data_id, existing_rec_id = \
                                         self._get_oeid_from_extid_or_alternative_keys(
                                                                cr, uid, vals, external_id,
                                                                external_session.referential_id.id,
                                                                alternative_keys, context=context)
                            vals_to_append = (0, 0, line)
                            if existing_rec_id:
                                sub_external_id = line.get('external_id')
                                if mapping[sub_mapping_id].get('alternative_keys'):
                                    sub_alternative_keys = list(mapping[sub_mapping_id]['alternative_keys'])
                                    if self._columns.get(to_field):
                                        related_field = self._columns[to_field]._fields_id
                                    elif self._inherit_fields.get(to_field):
                                        related_field = self._inherit_fields[to_field][2]._fields_id
                                    sub_alternative_keys.append(related_field)
                                    line[related_field] = existing_rec_id
                                    #search id of the sub_mapping related to the id of the parent
                                    sub_existing_ir_model_data_id, sub_existing_rec_id = \
                                                sub_mapping_obj._get_oeid_from_extid_or_alternative_keys(
                                                                    cr, uid, line, sub_external_id,
                                                                    external_session.referential_id.id,
                                                                    sub_alternative_keys, context=context)
                                    del line[related_field]
                                    if sub_existing_rec_id:
                                        vals_to_append = (1, sub_existing_rec_id, line)
                        vals[to_field].append(vals_to_append)
                    else:
                        vals[to_field].append(line)

            elif sub_mapping['internal_type'] == 'many2one':
                if convertion_type == 'from_external_to_openerp':
                    res = sub_mapping_obj._record_one_external_resource(cr, uid, external_session, field_value,
                                defaults=sub_mapping_defaults, mapping=mapping, mapping_id=sub_mapping_id, context=context)
                    vals[to_field] = res.get('write_id') or res.get('create_id')
                else:
                    sub_resource = sub_mapping_obj.read(cr, uid, field_value[0], context=context)
                    transform_args[4] = sub_resource
                    vals[to_field] = sub_mapping_obj._transform_one_resource(*transform_args, **transform_kwargs)
            else:
                raise except_osv(_('User Error'),
                                     _('Error with mapping : %s. Sub mapping can be only apply on one2many, many2one or many2many fields') % (sub_mapping['name'],))
    return vals


########################################################################################################################
#
#                                           END GENERIC TRANSFORM FEATURES
#
########################################################################################################################
