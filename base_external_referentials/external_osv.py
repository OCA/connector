# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    Sharoon Thomas, Raphael Valyi
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

class external_osv(osv.osv):
    
    def prefixed_id(self, id):
        return self._name + '_' + str(id)
    
    def id_from_prefixed_id(self, prefixed_id):
        return prefixed_id.split(self._name + '_')[1]
    
    def referential_id(self, cr, uid, id):
        model_data_id = self.pool.get('ir.model.data').search(cr,uid,[('res_id','=', id),('model','=',self._name),('module', '=', 'base_external_referentials')])
        if model_data_id:
            return self.pool.get('ir.model.data').read(cr,uid,model_data_id[0],['external_referential_id'])['external_referential_id'][0]
        else:
            return False

    def extid_to_oeid(self, cr, uid, ids, external_referential_id):
        #First get the external key field name
        #conversion external id -> OpenERP object using Object mapping_column_name key!
        mapping_id = self.pool.get('external.mapping').search(cr, uid, [('model', '=', self._name), ('referential_id', '=', external_referential_id)])
        if mapping_id:
            model_data_ids = self.pool.get('ir.model.data').search(cr,uid,[('name','=', self.prefixed_id(ids)),('model','=',self._name),('external_referential_id','=',external_referential_id)])
            if model_data_ids:
                oe_id = self.pool.get('ir.model.data').read(cr,uid,model_data_ids[0],['res_id'])['res_id']
                if oe_id:
                    return oe_id
        return False
    
    def ext_import(self,cr, uid, data, external_referential_id, defaults={}, context={}):
        #Inward data has to be list of dictionary
        #This function will import a given set of data as list of dictionary into Open ERP
        if data:
            write_ids = []  #Will record ids of records modified, not sure if will be used
            create_ids = [] #Will record ids of newly created records, not sure if will be used
            mapping_id = self.pool.get('external.mapping').search(cr,uid,[('model','=',self._name),('referential_id','=',external_referential_id)])
            if mapping_id:
                #If a mapping exists for current model, search for mapping lines
                mapping_line_ids = self.pool.get('external.mapping.line').search(cr,uid,[('mapping_id','=',mapping_id),('type','in',['in_out','in'])])
                mapping_lines = self.pool.get('external.mapping.line').read(cr,uid,mapping_line_ids,['external_field','external_type','in_function'])
                if mapping_lines:
                    #if mapping lines exist find the data conversion for each row in inward data
                    for each_row in data:
                        vals = {} #Dictionary for create record
                        for each_mapping_line in mapping_lines:
                            #Type cast if the expression exists
                            if each_mapping_line['external_type']:
                                type_casted_field = eval(each_mapping_line['external_type'])(each_row.get(each_mapping_line['external_field'],False))
                            else:
                                type_casted_field = each_row.get(each_mapping_line['external_field'],False)
                            #Build the space for expr
                            space = {
                                    'self':self,
                                    'cr':cr,
                                    'uid':uid,
                                    'data':each_row,
                                    'external_referential_id':external_referential_id,
                                    'defaults':defaults,
                                    'context':context,
                                    'ifield':type_casted_field,
                                    'conn':context.get('conn_obj',False),
                                    'base64':base64
                                        }
                            #The expression should return value in list of tuple format
                            #eg[('name','Sharoon'),('age',20)] -> vals = {'name':'Sharoon', 'age':20}
                            exec each_mapping_line['in_function'] in space
                            result = space.get('result',False)
                            #If result exists and is of type list
                            if result and type(result)==list:
                                for each_tuple in result:
                                    if type(each_tuple)==tuple and len(each_tuple)==2:
                                        vals[each_tuple[0]] = each_tuple[1] 
                        #Every mapping line has now been translated into vals dictionary, now set defaults if any
                        for each_default_entry in defaults.keys():
                            vals[each_default_entry] = defaults[each_default_entry]
                        #Vals is complete now, perform a record check, for that we need foreign field
                        for_key_field = self.pool.get('external.mapping').read(cr,uid,mapping_id[0],['external_key_name'])['external_key_name']
                        if vals and for_key_field in vals.keys():
                            external_id = vals[for_key_field]
                            #del vals[for_key_field] looks like it is affecting the import :(
                            #Check if record exists
                            existing_ir_model_data_id = self.pool.get('ir.model.data').search(cr, uid, [('model', '=', self._name), ('name', '=', self.prefixed_id(external_id))])
                            if existing_ir_model_data_id:
                                existing_rec_id = self.pool.get('ir.model.data').read(cr, uid, existing_ir_model_data_id, ['res_id'])[0]['res_id']
                                if self.write(cr,uid,existing_rec_id,vals,context):
                                    write_ids.append(existing_rec_id)
                            else:
                                crid = self.create(cr,uid,vals,context)
                                create_ids.append(crid)
                                ir_model_data_vals = {
                                        'name':self.prefixed_id(external_id),
                                        'model':self._name,
                                        'res_id':crid,
                                        'external_referential_id':external_referential_id,
                                        'module':'base_external_referentials'
                                                      }
                                self.pool.get('ir.model.data').create(cr,uid,ir_model_data_vals)

    def ext_export_data(self,cr,uid,ids,external_referential_id,defaults={},context={}):
        #if ids is [] all records are selected or ids has to be a list of ids
        #return a list of dictionary of formatted items
        if external_referential_id:
            out_data = []
            if not ids:
                ids = self.search(cr,uid,[])#Get all records if ids is empty
            data = self.read(cr,uid,ids,[])
            #Find the mapping record now
            mapping_id = self.pool.get('external.mapping').search(cr,uid,[('model','=',self._name),('referential_id','=',external_referential_id)])
            if mapping_id:
                #If a mapping exists for current model, search for mapping lines
                mapping_line_ids = self.pool.get('external.mapping.line').search(cr,uid,[('mapping_id','=',mapping_id),('type','in',['in_out','out'])])
                mapping_lines = self.pool.get('external.mapping.line').read(cr,uid,mapping_line_ids,['external_field','out_function'])
                if mapping_lines:
                    #if mapping lines exist find the data conversion for each row in inward data
                    for each_row in data:
                        vals = {} #Dictionary for record
                        for each_mapping_line in mapping_lines:
                            #Build the space for expr
                            space = {
                                    'self':self,
                                    'cr':cr,
                                    'uid':uid,
                                    'data':data,
                                    'external_referential_id':external_referential_id,
                                    'defaults':defaults,
                                    'context':context,
                                    'record':each_row,
                                    'conn':context.get('conn_obj',False),
                                    'base64':base64
                                    }
                            #The expression should return value in list of tuple format
                            #eg[('name','Sharoon'),('age',20)] -> vals = {'name':'Sharoon', 'age':20}
                            if each_mapping_line['out_function']:
                                exec each_mapping_line['out_function'] in space
                                result = space.get('result',False)
                                #If result exists and is of type list
                                if result and type(result)==list:
                                    for each_tuple in result:
                                        if type(each_tuple)==tuple and len(each_tuple)==2:
                                            vals[each_tuple[0]] = each_tuple[1]
                        #Every mapping line has now been translated into vals dictionary, now set defaults if any
                        for each_default_entry in defaults.keys():
                            vals[each_default_entry] = defaults[each_default_entry]
                        #If vals exist append it to the out_data list
                        if vals:
                            out_data.append(vals)
        return out_data
    
    def ext_export(self,cr, uid, ids, external_referential_ids=[], defaults={}, context={}):
        #external_referential_ids has to be alist
        if not ids:
            ids = self.search(cr,uid,[])
        for id in ids:
            #If no external_ref_ids are mentioned, then take all ext_ref_this item has
            if not external_referential_ids:
                ir_model_data_recids = self.pool.get('ir.model.data').search(cr,uid,[('model','=',self._name),('res_id','=',id),('module','=','base_external_referentials')])
                if ir_model_data_recids:
                    for each_model_rec in self.pool.get('ir.model.data').read(cr,uid,ir_model_data_recids,['external_referential_id']):
                        if each_model_rec['external_referential_id']:
                            external_referential_ids.append(each_model_rec['external_referential_id'][0])
            #if still theres no external_referential_ids then export to all referentials
            if not external_referential_ids:
                external_referential_ids = self.pool.get('external.referential').search(cr,uid,[])
            #Do an export for each external ID
            for each_ext_ref in external_referential_ids:
                exp_data = self.ext_export_data(cr, uid, [id], each_ext_ref, defaults, context)
                if exp_data and len(exp_data)==1:
                    #Check if export for this referential demands a create or update
                    rec_check_ids = self.pool.get('ir.model.data').search(cr,uid,[('model','=',self._name),('res_id','=',id),('module','=','base_external_referentials'),('external_referential_id','=',each_ext_ref)])
                    #rec_check_ids will indicate if the product already has a mapping record with ext system
                    mapping_id = self.pool.get('external.mapping').search(cr,uid,[('model','=',self._name),('referential_id','=',each_ext_ref)])
                    if mapping_id and len(mapping_id)==1:
                        mapping_rec = self.pool.get('external.mapping').read(cr,uid,mapping_id[0],['external_update_method','external_create_method'])
                        conn = context.get('conn_obj',False)
                        if rec_check_ids and mapping_rec and len(rec_check_ids)==1:
                            #The record was either imported or previously exported, so go for update
                            #Remove prefix and get remote record id
                            prefixed_id = self.pool.get('ir.model.data').read(cr,uid,rec_check_ids[0],['name'])['name']
                            ext_id = int(self.id_from_prefixed_id(prefixed_id))
                            #Record exists only update is required
                            if conn and mapping_rec['external_update_method']:
                                self.ext_update(cr, uid, exp_data[0], conn, mapping_rec['external_update_method'], ext_id)
                        else:
                            #Record needs to be created
                            if conn and mapping_rec['external_create_method']:
                                crid = self.ext_create(cr, uid, exp_data[0], conn, mapping_rec['external_create_method'])
                                ir_model_data_vals = {
                                        'name':self.prefixed_id(crid),
                                        'model':self._name,
                                        'res_id':id,
                                        'external_referential_id':each_ext_ref,
                                        'module':'base_external_referentials'
                                                      }
                                self.pool.get('ir.model.data').create(cr,uid,ir_model_data_vals)
    
    def ext_create(self,cr,uid,data,conn,method):
        return conn.call(method,data)
    
    def ext_update(self,cr,uid,data,conn,method,existing_id):    
        conn.call(method,[existing_id,data])