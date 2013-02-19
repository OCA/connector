# -*- encoding: utf-8 -*-
###############################################################################
#                                                                             #
#   product_custom_attributes for OpenERP                                     #
#   Copyright (C) 2012 Camptocamp Alexandre Fayolle  <alexandre.fayolle@camptocamp.com>  #
#   Copyright (C) 2012 Akretion Sebastien Beau <sebastien.beau@akretion.com>  #
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


from openerp.tools.translate import _

class ConnectorRegistry(object):
    def __init__(self):
        self.connectors = set()
        self.mappings = set()

    def get_connector(self, type, version):
        for connector in self.connectors:
            if connector.match(type, version):
                return connector
        raise ValueError('No matching connector found')

    def get_mapping(self, type, version):
        for mapping in self.mappings:
            if mapping.match(type, version):
                return mapping
        raise ValueError('No matching mapping found')

    def register_connector(self, connector):
        self.connectors.add(connector)

    def register_mapping(self, mapping):
        self.mappings.add(mapping)

REGISTRY = ConnectorRegistry()

class AbstractConnector(object):
    """base class for the connector

    subclasses can implement default implementations shared by different models for

    * _default_import_resource
    * _default_ext_read
    * _default_ext_search
    * _default_ext_search_read

    subclasses can implement the following specialization point:
    * _ext_read_<model_name>
    * _ext_search_<model_name>
    * _ext_search_read_<model_name>
    * _import_<model_name>(cr, uid, res_obj, defaults, context)
    * _get_import_defaults_<model_name>(cr, uid, context=context)
    * _import_<model_name>(cr, uid, res_obj, defaults, context)
    * _get_import_step_<model_name>(res_obj, context)
    * _get_filter_<model_name>(cr, uid, res_obj, step, previous_filter, context)
    * _record_one_<model_name>(cr, uid, res_obj, resource, defaults, context)
    * _oe_update_<model_name>(cr, uid, res_obj, existing_rec_id, vals, resource, defaults, context)
    * _oe_create_<model_name>(cr, uid, res_obj, vals, resource, defaults, context)
    """
    default_import_step = 100
    @classmethod
    def match(cls, type, version):
        return False # must be reimplemented in concrete class

    def _get_meth(self, name, res_obj, default=None):
        meth_name = name % res_obj._table
        meth = getattr(self, meth_name, None)
        if meth is not None:
            return meth
        else:
            return default

    def __init__(self, ext_session, referential):
        # XXX the session knows the referential, so maybe we can leave out 2nd arg
        self.ext_session = ext_session
        self.referential = referential
        self.pool = self.referential.pool
        self.mapping = REGISTRY.get_mapping(referential.type, referential.version)(self)
        self.logger = ext_session.logger

    def get_default_import_values(self, cr, uid, res_obj, context=None):
        meth = self._get_meth('_get_import_defaults_%s', res_obj)
        if meth is not None:
            return meth(cr, uid, context=context)
        return {}

    def import_resource(self, cr, uid, ressource_name, context=None):
        res_obj = self.pool.get(ressource_name)
        defaults = self.get_default_import_values(cr, uid, res_obj,
                                                  context=context)
        import_meth = self._get_meth('_import_%s', res_obj,
                                    self._default_import_resource,
                                    context=context)
        return import_meth(cr, uid, res_obj, defaults, context)

    def _default_import_resource(self, cr, uid, res_obj, defaults, context=None):
        """default import method, to be implemented on a per backend basis.

        choose the most often used import method for your backend and write something such as:

        return self._do_import_search_then_read(cr, uid, res_obj, defaults, context)
        """
        raise NotImplementedError()

    # boilerplate code for concrete implementations
    ## def _import_<ressource_name>(self, cr, uid, res_obj, defaults, context=None):
    ##     """write the code"""
    ##     return self._do_import_xxxx(cr, uid, res_obj, defaults, context)
    ##     return {'create_ids': [], write_ids:[]}

    def get_import_step(self, res_obj, context=None):
        meth = self._get_meth('_get_import_step_%s', res_obj, self.default_import_step)
        return meth(res_obj, context)

    def _do_import(self, cr, uid, res_obj, defaults, context=None):
        result = {"create_ids" : [], "write_ids" : []}
        step = self.get_import_step(res_obj, context)
        resource_filter = None
        while True:
            resource_filter = self.get_filter(cr, uid, res_obj,
                                              step,
                                              previous_filter=resource_filter,
                                              context=context)
            #TODO import only the field needed to improve speed import ;)
            resources = self.ext_search_read(res_obj, resource_filter, context)
            if not resources:
                break
            if not isinstance(resources, list):
                resources = [resources]
            res = self.record_ext_resources(cr, uid,
                                            res_obj,
                                            resources,
                                            defaults=defaults,
                                            context=context)
            for key in result:
                result[key] += res.get(key, [])
        return result


    def _do_import_noloop(self, cr, uid, res_obj, defaults, context=None):
        result = {"create_ids" : [],  "write_ids" : []}
        #Magento API do not support step import so we can not use a loop
        resource_filter = self.get_filter(cr, uid, res_obj, context=context)
        #TODO import only the field needed to improve speed import ;)
        resources = self.ext_search_read(res_obj, resource_filter, context)
        if not isinstance(resources, list):
            resources = [resources]
        res = self.record_ext_resources(cr, uid,
                                         res_obj,
                                        resources,
                                        defaults=defaults,
                                        context=context)
        for key in result:
            result[key] += res.get(key, [])
        return result

    def ext_read(self, res_obj, ext_ids, context=None):
        """return iterator over dict of object attributes"""
        meth = self._get_meth('_ext_read_%s', res_obj, self._default_ext_read)
        meth(res_obj, ext_ids, context=None)

    def _default_ext_read(self, res_obj, ext_ids, context=None):
        raise NotImplementedError

    def ext_search(self, res_obj, ext_filter, context=None):
        """return list of ext ids"""
        meth = self._get_meth('_ext_search_%s', res_obj, self._default_ext_search)
        meth(res_obj, ext_filter, context=None)

    def _default_ext_search(self, res_obj, ext_ids, context=None):
        raise NotImplementedError

    def ext_search_read(self, res_obj, ext_filter, context=None):
        """return list of dict of object attributes"""
        # default implementation, override with something smart if your backend allows / requires it
        meth = self._get_meth('_ext_search_read_%s', res_obj, self._default_ext_search_read)
        return meth(res_obj, ext_filter, context)

    def _default_ext_search_read(self, res_obj, ext_filter, context=None):
        ext_ids = self.ext_search(res_obj, ext_filter, context)
        return self.ext_read(res_obj, ext_ids, context)


    def get_filter(self, cr, uid, res_obj, step=None, previous_filter=None, context=None):
        meth = self._get_meth('_get_filter_%s', res_obj)
        if meth is not None:
            return meth(cr, uid, res_obj, step, previous_filter, context)
        return {}

    def record_ext_resources(self, cr, uid, res_obj, resources, defaults, context=None):
        if context is None:
            context = {}
        result = {'write_ids': [], 'create_ids': []}
        context['external_id_key_for_report'] = self.mapping.external_id_key_for_report(res_obj)
        for resource in resources:
            res = self.record_one_ext_resource(cr, uid, res_obj, resource, defaults, context)
            if 'create_id' in res:
                result['create_ids'].append(res['create_id'])
            if 'write_id'in res:
                result['write_ids'].append(res['write_id'])
        return result

    def record_one_ext_resource(self, cr, uid, res_obj, resource, defaults, context=None):
        meth = self._get_meth('_record_one_%s', res_obj, self._default_record_one_ext_resource)
        return meth(cr, uid, res_obj, resource, defaults, context)

    def _default_record_one_ext_resource(self, cr, uid, res_obj, resource, defaults, context):
        written = created = False
        vals = self.mapping.to_oerp(cr, uid, res_obj, resource, defaults, context)
        if not vals:
            # for example in the case of an update on existing resource if update is not wanted vals will be {}
            return {}
        referential_id = self.referential.id
        external_id = vals.get('external_id')
        external_id_ok = external_id not in (None, False)
        alternative_keys = self.mapping.alternative_keys(res_obj)
        if external_id_ok:
            del vals['external_id']
        existing_ir_model_data_id, existing_rec_id = res_obj._get_oeid_from_extid_or_alternative_keys\
                (cr, uid, vals, external_id, referential_id, alternative_keys, context=context)

        if not (external_id_ok or alternative_keys):
            self.logger.warning("The object imported needs an external_id, maybe the mapping doesn't exist for the object : %s" % res_obj._name)

        if existing_rec_id:
            if not res_obj._name in context.get('do_not_update', []):
                if self.oe_update(cr, uid, res_obj, existing_rec_id, vals, resource, defaults=defaults, context=context):
                    written = True
        else:
            existing_rec_id = self.oe_create(cr, uid,  res_obj, vals, resource, defaults, context=context)
            created = True

        if external_id_ok:
            if existing_ir_model_data_id:
                if created:
                    # means the external ressource is registred in ir.model.data but the ressource doesn't exist
                    # in this case we have to update the ir.model.data in order to point to the ressource created
                    self.pool.get('ir.model.data').write(cr, uid, existing_ir_model_data_id, {'res_id': existing_rec_id}, context=context)
            else:
                ir_model_data_vals = res_obj.create_external_id_vals(cr, uid,
                                                                     existing_rec_id,
                                                                     external_id,
                                                                     referential_id,
                                                                     context=context)
                if not created:
                    # means the external resource is bound to an already existing resource
                    # but not registered in ir.model.data, we log it to inform the success of the binding
                    self.logger.info("Bound in OpenERP %s from External Ref with "
                                     "external_id %s and OpenERP id %s successfully" % (res_obj._name,
                                                                                        external_id,
                                                                                        existing_rec_id))

        if created:
            if external_id:
                self.logger.info(("Created in OpenERP %s from External Ref with"
                                  "external_id %s and OpenERP id %s successfully" % (res_obj._name,
                                                                                     external_id_ok and str(external_id),
                                                                                     existing_rec_id)))
            elif alternative_keys:
                self.logger.info(("Created in OpenERP %s from External Ref with"
                                  "alternative_keys %s and OpenERP id %s successfully" % (res_obj._name,
                                                                                          external_id_ok and str (vals.get(alternative_keys)),
                                                                                          existing_rec_id)))
            return {'create_id' : existing_rec_id}
        elif written:
            if external_id:
                self.logger.info(("Updated in OpenERP %s from External Ref with"
                                  "external_id %s and OpenERP id %s successfully" % (res_obj._name,
                                                                                     external_id_ok and str(external_id),
                                                                                     existing_rec_id)))
            elif alternative_keys:
                self.logger.info(("Updated in OpenERP %s from External Ref with"
                                  "alternative_keys %s and OpenERP id %s successfully" % (res_obj._name,
                                                                                          external_id_ok and str (vals.get(alternative_keys)),
                                                                                          existing_rec_id)))
            return {'write_id' : existing_rec_id}
        return {}

    def oe_update(self, cr, uid, res_obj, existing_rec_id, vals, resource, defaults, context=None):
        """Update an existing resource in OpenERP

        :param ExternalSession external_session : External_session that contain all params of connection
        :param int existing_rec_id: openerp id to update
        :param dict vals: vals to write
        :param dict resource: resource to convert into OpenERP data
        :param dict defaults: default values
        :rtype boolean
        :return: True
        """
        if context is None:
            context={}
        context['referential_id'] = self.referential.id # is it needed somewhere?
        meth = self._get_meth('_oe_update_%s', res_obj)
        if meth is not None:
            return meth(cr, uid, res_obj, existing_rec_id, vals, resource, defaults, context)
        else:
            return res_obj.write(cr, uid, existing_rec_id, vals, context)

    def oe_create(self, cr, uid, res_obj, vals, resource, defaults, context=None):
        """Create an new resource in OpenERP

        :param ExternalSession external_session : External_session that contain all params of connection
        :param dict vals: vals to create
        :param dict resource: resource to convert into OpenERP data
        :param dict defaults: default values
        :rtype int
        :return: the id of the resource created
        """
        if context is None:
            context={}
        context['referential_id'] = self.referential.id  # is it needed somewhere?
        meth = self._get_meth('_oe_create_%s', res_obj)
        if meth is not None:
            return meth(cr, uid, res_obj, vals, resource, defaults, context)
        else:
            return res_obj.create(cr, uid, vals, context)


class AbstractMapping(object):
    maps = {}
    @classmethod
    def match(cls, type, version):
        return False # must be reimplemented in concrete class

    @classmethod
    def register_model_map(cls, map):
        cls.maps[map.model_name] = map

    def __init__(self, connector):
        self.connector = connector

    def map(self, res_obj):
        return self.maps[res_obj._name](self.connector)

    def to_oerp(self, cr, uid, res_obj, resource, defaults, context):
        return self.map(res_obj).to_oerp(cr, uid, resource, defaults, context)

    def external_id_key_for_report(self, res_obj):
        return self.map(res_obj).external_id_key_for_report()
        raise NotImplementedError # use key for external id if
                                  # available and alternative key
                                  # otherwise

        ##     if self.mapping.key_for_external_id(res_obj):
        ##     context['external_id_key_for_report'] = self.mapping.key_for_external_id(res_obj)
        ## else:
        ##     for field in self.mapping.mapping_lines(res_obj):
        ##         if field['alternative_key']:
        ##             context['external_id_key_for_report'] = field['external_field']
        ##             break



    def mapping_lines(self, res_obj):
        pass

class ModelMap(object):
    model_name = None # name of the OERP model
    _external_id_key = None
    direct_import = []
    function_import = []
    submapping_import = []
    direct_export = []
    function_export = []
    submapping_export = []

    def __init__(self, connector):
        self.connector = connector
        self.res_obj = self.connector.pool.get(self.model_name)

    def to_oerp(self, cr, uid, resource, defaults, parent_values=None, context=None):
        """
        parent_values is the result of the mapping of the containing obj (e.g. sale_order for a sale_order_line
        """
        result = defaults.copy()
        for ext_attr, oerp_attr in self.direct_import:
            result[oerp_attr] = resource.get(ext_attr, False)
        for ext_attr, meth in self.function_import:
            meth(self, cr, uid, ext_attr, resource, result, None)
        for ext_attr, (oerp_attr, submap_cls) in self.submapping_import:
            to_map = resource[ext_attr]
            submap = submap_cls(self.connector)
            if isinstance(to_map, list):
                res = submap._o2m_to_oerp(cr, uid, to_map, parent_value=result, context=context)
            else:
                res = submap._m2o_to_oerp(cr, uid, to_map, parent_value=result, context=context)
            result[oerp_attr] = res
        return result

    def _o2m_to_oerp(self, cr, uid, resources, parent_values=None, context=None):
        defaults = self.connector.get_default_import_values(cr, uid, self.res_obj,
                                                            context=context)
        result = []
        for resource in resources:
            res = self.to_oerp(cr, uid, resource, defaults, parent_values, context)
            result.append((0, 0, res))
        return result

    def _m2o_to_oerp(self, cr, uid, resource, parent_values=None, context=None):
        if parent_values is not None:
            if context is None:
                context = {}
            context = context.copy()
            context['recursive_import_from'] = parent_values
        defaults = self.connector.get_default_import_values(cr, uid, self.res_obj,
                                                            context=context)
        res = self.connector.record_one_ext_resource(cr, uid, self.res_obj,
                                                     resource, defaults, context)
        if 'create_id' in res:
            return res['create_id']
        else:
            return res['write_id']

    def external_id_key_for_report(self):
        return self._external_id_key or self.alternative_key()

    def alternative_key(self):
        raise NotImplementedError

