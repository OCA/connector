# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    Sharoon Thomas, Raphaël Valyi
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
import datetime
import netsvc

class external_osv(osv.osv):
    
    def prefixed_id(self, id):
        return self._name + '_' + str(id)
    
    def id_from_prefixed_id(self, prefixed_id):
        return prefixed_id.split(self._name + '_')[1]
    
    def get_last_imported_external_id(self, cr, object_name, referential_id, where_clause):
        table_name = object_name.replace('.', '_')
        cr.execute("""
                   SELECT %(table_name)s.id, ir_model_data.name from %(table_name)s inner join ir_model_data
                   ON %(table_name)s.id = ir_model_data.res_id
                   WHERE ir_model_data.model=%%s %(where_clause)s
                     AND ir_model_data.external_referential_id = %%s
                   ORDER BY %(table_name)s.create_date DESC
                   LIMIT 1
                   """ % { 'table_name' : table_name, 'where_clause' : where_clause and ("and " + where_clause) or ""}
                   , (object_name, referential_id,))
        results = cr.fetchone()
        if results and len(results) > 0:
            return [results[0], results[1].split(object_name +'_')[1]]
        else:
            return [False, False]
    
    def external_connection(self, cr, uid, DEBUG=False):
        """Should be overridden to provide valid external referential connection"""
        return False
    
    def oeid_to_extid(self, cr, uid, id, external_referential_id, context=None):
        model_data_ids = self.pool.get('ir.model.data').search(cr, uid, [('model', '=', self._name), ('res_id', '=', id), ('external_referential_id', '=', external_referential_id)])
        if model_data_ids and len(model_data_ids) > 0:
            prefixed_id = self.pool.get('ir.model.data').read(cr, uid, model_data_ids[0], ['name'])['name']
            ext_id = int(self.id_from_prefixed_id(prefixed_id))
            return ext_id
        return False

    def extid_to_oeid(self, cr, uid, id, external_referential_id, context=None):
        #First get the external key field name
        #conversion external id -> OpenERP object using Object mapping_column_name key!
        if id:
            mapping_id = self.pool.get('external.mapping').search(cr, uid, [('model', '=', self._name), ('referential_id', '=', external_referential_id)])
            if mapping_id:
                model_data_ids = self.pool.get('ir.model.data').search(cr, uid, [('name', '=', self.prefixed_id(id)), ('model', '=', self._name), ('external_referential_id', '=', external_referential_id)])
                if model_data_ids:
                    claimed_oe_id = self.pool.get('ir.model.data').read(cr, uid, model_data_ids[0], ['res_id'])['res_id']
                    
                    #because OpenERP might keep ir_model_data (is it a bug?) for deleted records, we check if record exists:
                    ids = self.search(cr, uid, [('id', '=', claimed_oe_id)])
                    if ids:
                        return ids[0]
    
                try:
                    result = self.get_external_data(cr, uid, self.external_connection(cr, uid, self.pool.get('external.referential').browse(cr, uid, external_referential_id)), external_referential_id, {}, {'id':id})
                    if len(result['create_ids']) == 1:
                        return result['create_ids'][0]
                except Exception, error: #external system might return error because no such record exists
                    print error
        return False
    
    def oevals_from_extdata(self, cr, uid, external_referential_id, data_record, key_field, mapping_lines, defaults, context):
        if context is None:
            context = {}
        vals = {} #Dictionary for create record
        for each_mapping_line in mapping_lines:
            #Type cast if the expression exists
            if each_mapping_line['external_field'] in data_record.keys():
                try:
                    if each_mapping_line['external_type'] and type(data_record.get(each_mapping_line['external_field'], False)) != unicode:
                        type_casted_field = eval(each_mapping_line['external_type'])(data_record.get(each_mapping_line['external_field'], False))
                    else:
                        type_casted_field = data_record.get(each_mapping_line['external_field'], False)
                    if type_casted_field in ['None', 'False']:
                        type_casted_field = False
                except Exception, e:
                    type_casted_field = False
                #Build the space for expr
                space = {
                            'self':self,
                            'cr':cr,
                            'uid':uid,
                            'data':data_record,
                            'external_referential_id':external_referential_id,
                            'defaults':defaults,
                            'context':context,
                            'ifield':type_casted_field,
                            'conn':context.get('conn_obj', False),
                            'base64':base64,
                            'vals':vals
                        }
                #The expression should return value in list of tuple format
                #eg[('name','Sharoon'),('age',20)] -> vals = {'name':'Sharoon', 'age':20}
                try:
                    exec each_mapping_line['in_function'] in space
                except Exception, e:
                    logger = netsvc.Logger()
                    logger.notifyChannel('extdata_from_oevals', netsvc.DEBUG, "Error in import mapping: %r" % (each_mapping_line['in_function'],))
                    del(space['__builtins__'])
                    logger.notifyChannel('extdata_from_oevals', netsvc.DEBUG, "Mapping Context: %r" % (space,))
                    logger.notifyChannel('extdata_from_oevals', netsvc.DEBUG, "Exception: %r" % (e,))
                result = space.get('result', False)
                #If result exists and is of type list
                if result and type(result) == list:
                    for each_tuple in result:
                        if type(each_tuple) == tuple and len(each_tuple) == 2:
                            vals[each_tuple[0]] = each_tuple[1] 
        #Every mapping line has now been translated into vals dictionary, now set defaults if any
        for each_default_entry in defaults.keys():
            vals[each_default_entry] = defaults[each_default_entry]

        return vals

        
    def get_external_data(self, cr, uid, conn, external_referential_id, defaults=None, context=None):
        """Constructs data using WS or other synch protocols and then call ext_import on it"""
        return {'create_ids': [], 'write_ids': []}

    def ext_import(self, cr, uid, data, external_referential_id, defaults=None, context=None):
        if defaults is None:
            defaults = {}
        if context is None:
            context = {}

        #Inward data has to be list of dictionary
        #This function will import a given set of data as list of dictionary into Open ERP
        write_ids = []  #Will record ids of records modified, not sure if will be used
        create_ids = [] #Will record ids of newly created records, not sure if will be used
        logger = netsvc.Logger()
        if data:
            mapping_id = self.pool.get('external.mapping').search(cr, uid, [('model', '=', self._name), ('referential_id', '=', external_referential_id)])
            if mapping_id:
                #If a mapping exists for current model, search for mapping lines
                mapping_line_ids = self.pool.get('external.mapping.line').search(cr, uid, [('mapping_id', '=', mapping_id), ('type', 'in', ['in_out', 'in'])])
                mapping_lines = self.pool.get('external.mapping.line').read(cr, uid, mapping_line_ids, ['external_field', 'external_type', 'in_function'])
                if mapping_lines:
                    #if mapping lines exist find the data conversion for each row in inward data
                    for_key_field = self.pool.get('external.mapping').read(cr, uid, mapping_id[0], ['external_key_name'])['external_key_name']
                    for each_row in data:
                        vals = self.oevals_from_extdata(cr, uid, external_referential_id, each_row, for_key_field, mapping_lines, defaults, context)
                        #perform a record check, for that we need foreign field
                        external_id = vals.get(for_key_field, False) or each_row.get(for_key_field, False) or each_row.get('external_id', False)
                        #del vals[for_key_field] looks like it is affecting the import :(
                        #Check if record exists
                        existing_ir_model_data_id = self.pool.get('ir.model.data').search(cr, uid, [('model', '=', self._name), ('name', '=', self.prefixed_id(external_id)), ('external_referential_id', '=', external_referential_id)])
                        record_test_id = False
                        if existing_ir_model_data_id:
                            existing_rec_id = self.pool.get('ir.model.data').read(cr, uid, existing_ir_model_data_id, ['res_id'])[0]['res_id']

                            #Note: OpenERP cleans up ir_model_data which res_id records have been deleted only at server update because that would be a perf penalty,
                            #so we take care of it here:
                            record_test_id = self.search(cr, uid, [('id', '=', existing_rec_id)])
                            if not record_test_id:
                                self.pool.get('ir.model.data').unlink(cr, uid, existing_ir_model_data_id)

                        if record_test_id:
                            if vals.get(for_key_field, False):
                                del vals[for_key_field]
                            if self.oe_update(cr, uid, existing_rec_id, vals, each_row, external_referential_id, defaults, context):
                                write_ids.append(existing_rec_id)
                                self.pool.get('ir.model.data').write(cr, uid, existing_ir_model_data_id, {'res_id':existing_rec_id})
                                logger.notifyChannel('ext synchro', netsvc.LOG_INFO, "Updated in OpenERP %s from External Ref with external_id %s and OpenERP id %s successfully" %(self._name, external_id, existing_rec_id))

                        else:
                            crid = self.oe_create(cr, uid, vals, each_row, external_referential_id, defaults, context)
                            create_ids.append(crid)
                            ir_model_data_vals = {
                                'name': self.prefixed_id(external_id),
                                'model': self._name,
                                'res_id': crid,
                                'external_referential_id': external_referential_id,
                                'module': 'extref.' + self.pool.get('external.referential').read(cr, uid, external_referential_id, ['name'])['name']
                            }
                            self.pool.get('ir.model.data').create(cr, uid, ir_model_data_vals)
                            logger.notifyChannel('ext synchro', netsvc.LOG_INFO, "Created in OpenERP %s from External Ref with external_id %s and OpenERP id %s successfully" %(self._name, external_id, crid))
                        cr.commit()

        return {'create_ids': create_ids, 'write_ids': write_ids}

    def oe_update(self, cr, uid, existing_rec_id, vals, data, external_referential_id, defaults, context):
        return self.write(cr, uid, existing_rec_id, vals, context)
 
    
    def oe_create(self, cr, uid, vals, data, external_referential_id, defaults, context):
        return self.create(cr, uid, vals, context)
    

    def extdata_from_oevals(self, cr, uid, external_referential_id, data_record, mapping_lines, defaults, context=None):
        if context is None:
            context = {}
        vals = {} #Dictionary for record
        for each_mapping_line in mapping_lines:
            #Build the space for expr
            space = {
                'self':self,
                'cr':cr,
                'uid':uid,
                'external_referential_id':external_referential_id,
                'defaults':defaults,
                'context':context,
                'record':data_record,
                'conn':context.get('conn_obj', False),
                'base64':base64
            }
            #The expression should return value in list of tuple format
            #eg[('name','Sharoon'),('age',20)] -> vals = {'name':'Sharoon', 'age':20}
            if each_mapping_line['out_function']:
                try:
                    exec each_mapping_line['out_function'] in space
                except Exception, e:
                    logger = netsvc.Logger()
                    logger.notifyChannel('extdata_from_oevals', netsvc.DEBUG, "Error in import mapping: %r" % (each_mapping_line['out_function'],))
                    del(space['__builtins__'])
                    logger.notifyChannel('extdata_from_oevals', netsvc.DEBUG, "Mapping Context: %r" % (space,))
                    logger.notifyChannel('extdata_from_oevals', netsvc.DEBUG, "Exception: %r" % (e,))

                result = space.get('result', False)
                #If result exists and is of type list
                if result and type(result) == list:
                    for each_tuple in result:
                        if type(each_tuple) == tuple and len(each_tuple) == 2:
                            vals[each_tuple[0]] = each_tuple[1]
        #Every mapping line has now been translated into vals dictionary, now set defaults if any
        for each_default_entry in defaults.keys():
            vals[each_default_entry] = defaults[each_default_entry]
            
        return vals

    
    def ext_export(self, cr, uid, ids, external_referential_ids=[], defaults={}, context=None):
        if context is None:
            context = {}
        #external_referential_ids has to be a list
        logger = netsvc.Logger()
        write_ids = []  #Will record ids of records modified, not sure if will be used
        create_ids = [] #Will record ids of newly created records, not sure if will be used
        for record_data in self.read(cr, uid, ids, [], context):
            #If no external_ref_ids are mentioned, then take all ext_ref_this item has
            if not external_referential_ids:
                ir_model_data_recids = self.pool.get('ir.model.data').search(cr, uid, [('model', '=', self._name), ('res_id', '=', id), ('module', 'ilike', 'extref')])
                if ir_model_data_recids:
                    for each_model_rec in self.pool.get('ir.model.data').read(cr, uid, ir_model_data_recids, ['external_referential_id']):
                        if each_model_rec['external_referential_id']:
                            external_referential_ids.append(each_model_rec['external_referential_id'][0])
            #if still there no external_referential_ids then export to all referentials
            if not external_referential_ids:
                external_referential_ids = self.pool.get('external.referential').search(cr, uid, [])
            #Do an export for each external ID
            for ext_ref_id in external_referential_ids:
                #Find the mapping record now
                mapping_id = self.pool.get('external.mapping').search(cr, uid, [('model', '=', self._name), ('referential_id', '=', ext_ref_id)])
                if mapping_id:
                    #If a mapping exists for current model, search for mapping lines
                    mapping_line_ids = self.pool.get('external.mapping.line').search(cr, uid, [('mapping_id', '=', mapping_id), ('type', 'in', ['in_out', 'out'])])
                    mapping_lines = self.pool.get('external.mapping.line').read(cr, uid, mapping_line_ids, ['external_field', 'out_function'])
                    if mapping_lines:
                        #if mapping lines exist find the data conversion for each row in inward data
                        exp_data = self.extdata_from_oevals(cr, uid, ext_ref_id, record_data, mapping_lines, defaults, context)
                        #Check if export for this referential demands a create or update
                        rec_check_ids = self.pool.get('ir.model.data').search(cr, uid, [('model', '=', self._name), ('res_id', '=', record_data['id']), ('module', 'ilike', 'extref'), ('external_referential_id', '=', ext_ref_id)])
                        #rec_check_ids will indicate if the product already has a mapping record with ext system
                        mapping_id = self.pool.get('external.mapping').search(cr, uid, [('model', '=', self._name), ('referential_id', '=', ext_ref_id)])
                        if mapping_id and len(mapping_id) == 1:
                            mapping_rec = self.pool.get('external.mapping').read(cr, uid, mapping_id[0], ['external_update_method', 'external_create_method'])
                            conn = context.get('conn_obj', False)
                            if rec_check_ids and mapping_rec and len(rec_check_ids) == 1:
                                ext_id = self.oeid_to_extid(cr, uid, record_data['id'], ext_ref_id, context)

                                if not context.get('force', False):
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
                                        last_exported_time = datetime.datetime.fromtimestamp(time.mktime(time.strptime(last_exported_time, '%Y-%m-%d %H:%M:%S')))
                                        last_updated_time = datetime.datetime.fromtimestamp(time.mktime(time.strptime(last_updated_time, '%Y-%m-%d %H:%M:%S')))
                                        if last_exported_time + datetime.timedelta(seconds=1) > last_updated_time:
                                            continue

                                if conn and mapping_rec['external_update_method']:
                                    self.ext_update(cr, uid, exp_data, conn, mapping_rec['external_update_method'], record_data['id'], ext_id, rec_check_ids[0], mapping_rec['external_create_method'], context)
                                    write_ids.append(record_data['id'])
                                    #Just simply write to ir.model.data to update the updated time
                                    ir_model_data_vals = {
                                                            'res_id': record_data['id'],
                                                          }
                                    self.pool.get('ir.model.data').write(cr, uid, rec_check_ids[0], ir_model_data_vals)
                                    logger.notifyChannel('ext synchro', netsvc.LOG_INFO, "Updated in External Ref %s from OpenERP with external_id %s and OpenERP id %s successfully" %(self._name, ext_id, record_data['id']))
                            else:
                                #Record needs to be created
                                if conn and mapping_rec['external_create_method']:
                                    crid = self.ext_create(cr, uid, exp_data, conn, mapping_rec['external_create_method'], record_data['id'], context)
                                    create_ids.append(record_data['id'])
                                    ir_model_data_vals = {
                                                            'name': self.prefixed_id(crid),
                                                            'model': self._name,
                                                            'res_id': record_data['id'],
                                                            'external_referential_id': ext_ref_id,
                                                            'module': 'extref.' + self.pool.get('external.referential').read(cr, uid, ext_ref_id, ['name'])['name']
                                                          }
                                    self.pool.get('ir.model.data').create(cr, uid, ir_model_data_vals)
                                    logger.notifyChannel('ext synchro', netsvc.LOG_INFO, "Created in External Ref %s from OpenERP with external_id %s and OpenERP id %s successfully" %(self._name, crid, record_data['id']))
                            cr.commit()
                            
        return {'create_ids': create_ids, 'write_ids': write_ids}


    def can_create_on_update_failure(self, error, data, context):
        return True

    def ext_create(self, cr, uid, data, conn, method, oe_id, context):
        return conn.call(method, data)
    
    def try_ext_update(self, cr, uid, data, conn, method, oe_id, external_id, ir_model_data_id, create_method, context):
        return conn.call(method, [external_id, data])
    
    def ext_update(self, cr, uid, data, conn, method, oe_id, external_id, ir_model_data_id, create_method, context):
        try:
            self.try_ext_update(cr, uid, data, conn, method, oe_id, external_id, ir_model_data_id, create_method, context)
        except Exception, e:
            logger = netsvc.Logger()
            logger.notifyChannel('ext synchro', netsvc.LOG_INFO, "UPDATE ERROR: %s" % e)
            if self.can_create_on_update_failure(e, data, context):
                logger.notifyChannel('ext synchro', netsvc.LOG_INFO, "may be the resource doesn't exist any more in the external referential, trying to re-create a new one")
                crid = self.ext_create(cr, uid, data, conn, create_method, oe_id, context)
                self.pool.get('ir.model.data').write(cr, uid, ir_model_data_id, {'name': self.prefixed_id(crid)})
                return crid
            
        
