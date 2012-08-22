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

    subclasses must implement the _import_<resource_name>(cursor,
    uid, res_obj, defaults, context) methods for the various resources
    """
    @classmethod
    def match(cls, type, version):
        return False # must be reimplemented in concrete class

    def __init__(self, ext_session, referential):
        # XXX the session knows the referential, so maybe we can leave out 2nd arg
        self.ext_session = ext_session
        self.referential = referential
        self.pool = self.referential.pool
        self.mapping = REGISTRY.get_mapping(referential.type, referential.version)

    def import_resource(self, cr, uid, ressource_name, context=None):
        res_obj = self.pool.get(ressource_name)
        defaults = res_obj._get_default_import_values(cursor, uid,
                                                      self.ext_session,
                                                      context=context)
        try:
            import_meth = getattr(self, '_import_%s' % ressource_name.replace('.', '_'))
        except AttributeError:
            self._default_import_resource(cr, uid, res_obj, defaults, context)
        else:
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

    def _do_import_searchread(self, cr, uid, res_obj, defaults, context=None):
        result = {"create_ids" : [], "write_ids" : []}
        step = res_obj._get_import_step(cr, uid, self.ext_session, context=context)
        resource_filter = None
        while True:
            resource_filter = res_obj._get_filter(cr, uid,
                                                  self.ext_session,
                                                  step,
                                                  previous_filter=resource_filter,
                                                  context=context)
            #TODO import only the field needed to improve speed import ;)
            resources = res_obj._get_external_resources(cr, uid,
                                                        self.ext_session,
                                                        resource_filter=resource_filter,
                                                        mapping=self.mapping,
                                                        fields=None,
                                                        context=context)
            if not resources:
                break
            if not isinstance(resources, list):
                resources = [resources]
            res = res_obj._record_external_resources(cr, uid,
                                                     self.ext_session,
                                                     resources,
                                                     defaults=defaults,
                                                     mapping=self.mapping,
                                                     context=context)
            for key in result:
                result[key] += res.get(key, [])
        return result

    def _do_import_search_then_read(self, cr, uid, res_obj, defaults, context=None):
        result = {"create_ids" : [], "write_ids" : []}
        step = res_obj._get_import_step(cr, uid, self.ext_session, context=context)
        resource_filter = None
        while True:
            resource_filter = res_obj._get_filter(cr, uid,
                                                  self.ext_session,
                                                  step,
                                                  previous_filter=resource_filter,
                                                  context=context)
            ext_ids = res_obj._get_external_resource_ids(cr, uid,
                                                         self.ext_session,
                                                         resource_filter,
                                                         mapping=self.mapping,
                                                         context=context)
            if not ext_ids:
                break
            for ext_id in ext_ids:
                #TODO import only the field needed to improve speed import ;)
                resources = res_obj._get_external_resources(cr, uid,
                                                            self.ext_session,
                                                            ext_id,
                                                            mapping=self.mapping,
                                                            fields=None,
                                                            context=context)
                if not isinstance(resources, list):
                    resources = [resources]
                res = res_obj._record_external_resources(cr, uid,
                                                         self.ext_session,
                                                         resources,
                                                         defaults=defaults,
                                                         mapping=self.mapping,
                                                         context=context)
                for key in result:
                    result[key] += res.get(key, [])
        return result

    def _do_import_searchread_noloop(self, cr, uid, res_obj, defaults, context=None):
        result = {"create_ids" : [], "write_ids" : []}
        step = res_obj._get_import_step(cr, uid, self.ext_session, context=context)
        #Magento API do not support step import so we can not use a loop
        resource_filter = res_obj._get_filter(cr, uid,
                                              self.ext_session,
                                              step,
                                              context=context)
        #TODO import only the field needed to improve speed import ;)
        resources = res_obj._get_external_resources(cr, uid,
                                                    self.ext_session,
                                                    resource_filter=resource_filter,
                                                    mapping=self.mapping,
                                                    fields=None,
                                                    context=context)
        if not isinstance(resources, list):
            resources = [resources]
        res = res_obj._record_external_resources(cr, uid,
                                                 self.ext_session,
                                                 resources,
                                                 defaults=defaults,
                                                 mapping=self.mapping,
                                                 context=context)
        for key in result:
            result[key] += res.get(key, [])
        return result

    def _do_import_search_then_read_noloop(self, cr, uid, res_obj, defaults, context=None):
        result = {"create_ids" : [], "write_ids" : []}
        step = res_obj._get_import_step(cr, uid, self.ext_session, context=context)
        #Magento API do not support step import so we can not use a loop
        resource_filter = res_obj._get_filter(cr, uid,
                                              self.ext_session,
                                              step,
                                              context=context)
        ext_ids = res_obj._get_external_resource_ids(cr, uid,
                                                     self.ext_session,
                                                     resource_filter,
                                                     mapping=self.mapping,
                                                     context=context)
        for ext_id in ext_ids:
            #TODO import only the field needed to improve speed import ;)
            self.update_filter_with_id(resource_filter, ext_id)
            resources = res_obj._get_external_resources(cr, uid,
                                                        self.ext_session,
                                                        ext_id,
                                                        mapping=self.mapping,
                                                        fields=None,
                                                        context=context)
            if not isinstance(resources, list):
                resources = [resources]
            res = res_obj._record_external_resources(cr, uid, self.ext_session,
                                                     resources,
                                                     defaults=defaults,
                                                     mapping=self.mapping,
                                                     context=context)
            for key in result:
                result[key] += res.get(key, [])
        return result

    def update_filter_with_id(self, resource_filter, ext_id):
        filter_key = self.mapping['key_for_external_id']
        resource_filter[filter_key] = external_id

    def ext_read(self, ext_ids, context=None):
        """return list dict of object attributes"""
        raise NotImplementedError

    def ext_search(self, ext_filter, context=None):
        """return list of ext ids"""
        raise NotImplementedError

    def ext_search_read(self, ext_filter, context=None):
        """return list of dict of object attributes"""
        raise NotImplementedError

class AbstractMapping(object):
    @classmethod
    def match(cls, type, version):
        return False # must be reimplemented in concrete class
