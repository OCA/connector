# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    Sharoon Thomas, Raphaël Valyi, Guewen Baconnier
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
import pooler

from tools.translate import _

class MappingError(Exception):
     def __init__(self, value, name):
         self.value = value
         self.mapping_name = name
     def __str__(self):
         return repr(self.value)
        
class ExtConnError(Exception):
     def __init__(self, value):
         self.value = value
     def __str__(self):
         return repr(self.value)


def read_w_order(self, cr, user, ids, fields_to_read=None, context=None, load='_classic_read'):
    res = self.read(cr, user, ids, fields_to_read, context, load)
    resultat = []
    for id in ids:
        resultat += [x for x in res if x['id'] == id]
    return resultat

def browse_w_order(self, cr, uid, ids, context=None, list_class=None, fields_process={}):
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
        return [results[0], results[1].split(object_name.replace('.', '_') +'/')[1]]
    else:
        return [False, False]

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

def external_connection(self, cr, uid, referential, DEBUG=False):
    """Should be overridden to provide valid external referential connection"""
    return False

def oeid_to_extid(self, cr, uid, id, external_referential_id, context=None):
    """Returns the external id of a resource by its OpenERP id.
    Returns False if the resource id does not exists."""
    if isinstance(id, list):
        id = id[0]
    model_data_ids = self.pool.get('ir.model.data').search(cr, uid, [('model', '=', self._name), ('res_id', '=', id), ('external_referential_id', '=', external_referential_id)])
    if model_data_ids and len(model_data_ids) > 0:
        prefixed_id = self.pool.get('ir.model.data').read(cr, uid, model_data_ids[0], ['name'])['name']
        ext_id = self.id_from_prefixed_id(prefixed_id)
        return ext_id
    return False

def extid_to_existing_oeid(self, cr, uid, id, external_referential_id, context=None):
    """Returns the OpenERP id of a resource by its external id.
       Returns False if the resource does not exist."""
    if id:
        model_data_ids = self.pool.get('ir.model.data').search(cr, uid, [('name', '=', self.prefixed_id(id)), ('model', '=', self._name), ('external_referential_id', '=', external_referential_id)])
        if model_data_ids:
            claimed_oe_id = self.pool.get('ir.model.data').read(cr, uid, model_data_ids[0], ['res_id'])['res_id']

            #because OpenERP might keep ir_model_data (is it a bug?) for deleted records, we check if record exists:
            ids = self.search(cr, uid, [('id', '=', claimed_oe_id)])
            if ids:
                return ids[0]
    return False

def extid_to_oeid(self, cr, uid, id, external_referential_id, context=None):
    """Returns the OpenERP ID of a resource by its external id.
    Creates the resource from the external connection if the resource does not exist."""
    #First get the external key field name
    #conversion external id -> OpenERP object using Object mapping_column_name key!
    if id:
        existing_id = self.extid_to_existing_oeid(cr, uid, id, external_referential_id, context)
        if existing_id:
            return existing_id
        try:
            if context and context.get('alternative_key', False): #FIXME dirty fix for Magento product.info id/sku mix bug: https://bugs.launchpad.net/magentoerpconnect/+bug/688225
                id = context.get('alternative_key', False)
            result = self.get_external_data(cr, uid, self.external_connection(cr, uid, self.pool.get('external.referential').browse(cr, uid, external_referential_id)), external_referential_id, {}, {'id':id})
            if len(result['create_ids']) == 1:
                return result['create_ids'][0]
        except Exception, error: #external system might return error because no such record exists
            print "===================== error when importing the %s on fly =================", self._name
            print error
    return False

def oevals_from_extdata(self, cr, uid, external_referential_id, data_record, key_field, mapping_lines, defaults, context):
    if context is None:
        context = {}
    vals = {} #Dictionary for create record
    #Set defaults if any
    for each_default_entry in defaults.keys():
        vals[each_default_entry] = defaults[each_default_entry]
    for each_mapping_line in mapping_lines:
        #Type cast if the expression exists
        if each_mapping_line['external_field'] in data_record.keys():
            ifield = data_record.get(each_mapping_line['external_field'], False)
            if ifield:
                if each_mapping_line['external_type'] == 'list' and isinstance(ifield, (str, unicode)):
                    casted_field = eval(ifield)
                    # For a list, external data may returns something like '1,2,3' but also '1' if only
                    # one item has been selected. So if the casted field is not iterable, we put it in a tuple: (1,)
                    if not hasattr(casted_field, '__iter__'):
                        casted_field = (casted_field,)
                    type_casted_field = list(casted_field)
                else:
                    type_casted_field = eval(each_mapping_line['external_type'])(ifield)
            else:
                if each_mapping_line['external_type'] == 'list':
                    type_casted_field = []
                else:
                    type_casted_field = ifield

            if type_casted_field in ['None', 'False']:
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
                logger.notifyChannel('extdata_from_oevals', netsvc.LOG_DEBUG, "Error in import mapping: %r" % (each_mapping_line['in_function'],))
                del(space['__builtins__'])
                logger.notifyChannel('extdata_from_oevals', netsvc.LOG_DEBUG, "Mapping Context: %r" % (space,))
                logger.notifyChannel('extdata_from_oevals', netsvc.LOG_DEBUG, "Exception: %r" % (e,))
                # For which purpose should we let the error go silently ? What is this dont_rais_error ?
                # I think that MappingError must always be raised and be catched at higher level
                if not context.get('dont_raise_error', False):
                    raise MappingError(e, each_mapping_line['external_field'])
            
            result = space.get('result', False)
            # Check if result returned by the mapping function is correct : [('field1': value), ('field2': value))]
            # And fill the vals dict with the results
            if result:
                if isinstance(result, list):
                    for each_tuple in result:
                        if isinstance(each_tuple, tuple) and len(each_tuple) == 2:
                            vals[each_tuple[0]] = each_tuple[1]
                else:
                    # same comment as upper
                    if not context.get('dont_raise_error', False):
                        raise MappingError(_('Invalid format for the variable result.'), each_mapping_line['external_field'])
    return vals


def get_external_data(self, cr, uid, conn, external_referential_id, defaults=None, context=None):
    """Constructs data using WS or other synch protocols and then call ext_import on it"""
    return {'create_ids': [], 'write_ids': []}


#TODO remove me, using a decorator will be better, also for a decorator should be added for export
def import_with_try(self, cr, uid, callback, data_record, external_referential_id, defaults, context=None):
    if not context:
        context={}
    res={}
    report_line_obj = self.pool.get('external.report.line')
    report_line_id = report_line_obj._log_base(cr, uid, self._name, callback.im_func.func_name, 
                                    state='fail', external_id=context.get('external_object_id', False),
                                    defaults=defaults, data_record=data_record, 
                                    context=context)
    context['report_line_id'] = report_line_id
    import_cr = pooler.get_db(cr.dbname).cursor()
    res = callback(import_cr, uid, data_record, external_referential_id, defaults, context=context)
    try:
        pass
        #res = callback(import_cr, uid, data_record, external_referential_id, defaults, context=context)
    except MappingError as e:
        import_cr.rollback()
        report_line_obj.write(cr, uid, report_line_id, {
                        'error_message': 'Error with the mapping : %s. Error details : %s'%(e.mapping_name, e.value),
                        }, context=context)
    except osv.except_osv as e:
        import_cr.rollback()
        raise osv.except_osv(*e)
    except Exception as e:
        import_cr.rollback()
        raise Exception(e)
    else:
        report_line_obj.write(cr, uid, report_line_id, {
                    'state': 'success',
                    }, context=context)
        import_cr.commit()
    finally:
        import_cr.close()
    return res

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
            mapping_line_ids = self.pool.get('external.mapping.line').search(cr, uid, [('mapping_id', '=', mapping_id[0]), ('type', 'in', ['in_out', 'in'])])
            mapping_lines = self.pool.get('external.mapping.line').read(cr, uid, mapping_line_ids, ['external_field', 'external_type', 'in_function'])
            if mapping_lines:
                #if mapping lines exist find the data conversion for each row in inward data
                for_key_field = self.pool.get('external.mapping').read(cr, uid, mapping_id[0], ['external_key_name'])['external_key_name']
                for each_row in data:
                    created = written = bound = False
                    vals = self.oevals_from_extdata(cr, uid, external_referential_id, each_row, for_key_field, mapping_lines, defaults, context)
                    #perform a record check, for that we need foreign field
                    #TODO seb asked : did the option "vals.get(for_key_field, False)" and "each_row.get('external_id', False)" are still usefull??
                    external_id = vals.get('external_id', False) or vals.get(for_key_field, False) or each_row.get(for_key_field, False) or each_row.get('external_id', False)
                    #del vals[for_key_field] looks like it is affecting the import :(
                    #Check if record exists
                    existing_ir_model_data_id = self.pool.get('ir.model.data').search(cr, uid, [('model', '=', self._name),
                                                                                                ('name', '=', self.prefixed_id(external_id)),
                                                                                                ('external_referential_id', '=', external_referential_id)])
                    existing_rec_id = False
                    if existing_ir_model_data_id:
                        existing_rec_id = self.pool.get('ir.model.data').read(cr, uid, existing_ir_model_data_id, ['res_id'])[0]['res_id']

                        #Note: OpenERP cleans up ir_model_data which res_id records have been deleted only at server update because that would be a perf penalty,
                        #so we take care of it here:
                        test_existing_rec_id = self.search(cr, uid, [('id', '=', existing_rec_id)])
                        if not test_existing_rec_id:
                            self.pool.get('ir.model.data').unlink(cr, uid, existing_ir_model_data_id)
                            existing_ir_model_data_id = existing_rec_id = False
                    else:
                        # alternative way to find an OpenERP resource to bind with the external resource
                        existing_rec_id = \
                        self._search_existing_id_by_vals(cr, uid, vals, external_id,
                                                         external_referential_id, defaults,
                                                         context=context)

                    if existing_rec_id:
                        if vals.get(for_key_field, False):
                            del vals[for_key_field]
                        if self.oe_update(cr, uid, existing_rec_id, vals, each_row, external_referential_id, defaults=defaults, context=context):
                            written = True
                            write_ids.append(existing_rec_id)
                        if not existing_ir_model_data_id:
                            # means the external resource is bound to an existing resource
                            # using the _search_existing_id_by_vals method
                            bound = True
                    else:
                        existing_rec_id = self.oe_create(cr, uid, vals, each_row, external_referential_id, defaults, context=context)
                        created = True

                    if existing_ir_model_data_id:
                        self.pool.get('ir.model.data').write(cr, uid, existing_ir_model_data_id, {'res_id': existing_rec_id}, context=context)
                    else:
                        ir_model_data_vals = \
                        self._prepare_external_id_vals(cr, uid, existing_rec_id,
                                                       external_id, external_referential_id,
                                                       defaults=defaults, context=context)
                        self.pool.get('ir.model.data').create(cr, uid, ir_model_data_vals, context=context)
                        if bound:
                            logger.notifyChannel('ext synchro', netsvc.LOG_INFO, "Bound in OpenERP %s from External Ref with external_id %s and OpenERP id %s successfully" %(self._name, external_id, existing_rec_id))

                    if created:
                        create_ids.append(existing_rec_id)
                        logger.notifyChannel('ext synchro', netsvc.LOG_INFO, "Created in OpenERP %s from External Ref with external_id %s and OpenERP id %s successfully" %(self._name, external_id, existing_rec_id))
                    elif written:
                        write_ids.append(existing_rec_id)
                        logger.notifyChannel('ext synchro', netsvc.LOG_INFO, "Updated in OpenERP %s from External Ref with external_id %s and OpenERP id %s successfully" %(self._name, external_id, existing_rec_id))

    return {'create_ids': create_ids, 'write_ids': write_ids}

def _search_existing_id_by_vals(self, cr, uid, vals, external_id, external_referential_id, defaults=None, context=None):
    """ Hook. Used to bind resources already existing in OpenERP when they are 
        imported from the external referential if no external id is found in ir.model.data.
        As instance, search a partner by the mail, once found, the mapping will 
        be written in ir.model.data and the existing customer updated.  
        Must return the id of the resource on which the external id must be binded.
        
        Return: ID of the resource
    """
    return False

def retry_import(self, cr, uid, id, ext_id, external_referential_id, defaults=None, context=None):
    """ When we import again a previously failed import
    """
    raise osv.except_osv(_("Not Implemented"), _("Not Implemented in abstract base module!"))

def oe_update(self, cr, uid, existing_rec_id, vals, data, external_referential_id, defaults, context):
    return self.write(cr, uid, existing_rec_id, vals, context)


def oe_create(self, cr, uid, vals, data, external_referential_id, defaults, context):
    return self.create(cr, uid, vals, context)


def extdata_from_oevals(self, cr, uid, external_referential_id, data_record, mapping_lines, defaults, context=None):
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
                logger.notifyChannel('extdata_from_oevals', netsvc.LOG_DEBUG, "Error in import mapping: %r" % (each_mapping_line['out_function'],))
                del(space['__builtins__'])
                logger.notifyChannel('extdata_from_oevals', netsvc.LOG_DEBUG, "Mapping Context: %r" % (space,))
                logger.notifyChannel('extdata_from_oevals', netsvc.LOG_DEBUG, "Exception: %r" % (e,))
                # For which purpose should we let the error go silently ? What is this dont_rais_error ?
                # I think that MappingError must always be raised and be catched at higher level
                if not context.get('dont_raise_error', False):
                    raise MappingError(e, each_mapping_line['external_field'])
            result = space.get('result', False)
            #If result exists and is of type list
            if result:
                if isinstance(result, list):
                    for each_tuple in result:
                        if isinstance(each_tuple, tuple) and len(each_tuple) == 2:
                            vals[each_tuple[0]] = each_tuple[1]
                else:
                    if not context.get('dont_raise_error', False):
                        raise MappingError(_('Invalid format for the variable result.'), each_mapping_line['external_field'])
    return vals


def ext_export(self, cr, uid, ids, external_referential_ids=[], defaults={}, context=None):
    if context is None:
        context = {}
    #external_referential_ids has to be a list
    logger = netsvc.Logger()
    report_line_obj = self.pool.get('external.report.line')
    write_ids = []  #Will record ids of records modified, not sure if will be used
    create_ids = [] #Will record ids of newly created records, not sure if will be used
    for record_data in self.read_w_order(cr, uid, ids, [], context):
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
                mapping_line_ids = self.pool.get('external.mapping.line').search(cr, uid, [('mapping_id', '=', mapping_id[0]), ('type', 'in', ['in_out', 'out'])])
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
                                    last_exported_time = datetime.datetime.fromtimestamp(time.mktime(time.strptime(last_exported_time, '%Y-%m-%d %H:%M:%S')))
                                    last_updated_time = datetime.datetime.fromtimestamp(time.mktime(time.strptime(last_updated_time, '%Y-%m-%d %H:%M:%S')))
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
                                    logger.notifyChannel('ext synchro', netsvc.LOG_INFO, "Updated in External Ref %s from OpenERP with external_id %s and OpenERP id %s successfully" %(self._name, ext_id, record_data['id']))
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
                                    ir_model_data_vals = self._prepare_external_id_vals(cr, uid, record_data['id'], crid, ext_ref_id, defaults=defaults, context=context)
                                    self.pool.get('ir.model.data').create(cr, uid, ir_model_data_vals)
                                    report_line_obj.log_success(cr, uid, self._name, 'export',
                                                                res_id=record_data['id'],
                                                                external_id=crid, defaults=defaults,
                                                                context=context)
                                    logger.notifyChannel('ext synchro', netsvc.LOG_INFO, "Created in External Ref %s from OpenERP with external_id %s and OpenERP id %s successfully" %(self._name, crid, record_data['id']))
                                except Exception, err:
                                    report_line_obj.log_failed(cr, uid, self._name, 'export',
                                                               res_id=record_data['id'],
                                                               exception=err, defaults=defaults,
                                                               context=context)
                        cr.commit()

    return {'create_ids': create_ids, 'write_ids': write_ids}

def _prepare_external_id_vals(self, cr, uid, res_id, ext_id, external_referential_id, defaults=None, context=None):
    """ Create an external reference for a resource id in the ir.model.data table"""
    ir_model_data_vals = {
                            'name': self.prefixed_id(ext_id),
                            'model': self._name,
                            'res_id': res_id,
                            'external_referential_id': external_referential_id,
                            'module': 'extref/' + self.pool.get('external.referential').\
                            read(cr, uid, external_referential_id, ['name'])['name']
                          }
    return ir_model_data_vals

def retry_export(self, cr, uid, id, ext_id, external_referential_id, defaults=None, context=None):
    """ When we export again a previously failed export
    """
    conn = self.external_connection(
        cr,
        uid,
        self.pool.get('external.referential').
        browse(cr, uid, external_referential_id))
    context['conn_obj'] = conn
    return self.ext_export(cr, uid, [id], [external_referential_id], defaults, context)

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

def report_action_mapping(self, cr, uid, context=None):
        """
        For each action logged in the reports, we associate
        the method to launch when we replay the action.
        """
        mapping = {
            'export': {'method': self.retry_export, 
                       'fields': {'id': 'log.res_id',
                                  'ext_id': 'log.external_id',
                                  'external_referential_id': 'log.external_report_id.external_referential_id.id',
                                  'defaults': 'log.origin_defaults',
                                  'context': 'log.origin_context',
                                  },
                    },
            'import': {'method': self.retry_import,
                       'fields': {'id': 'log.res_id',
                                  'ext_id': 'log.external_id',
                                  'external_referential_id': 'log.external_report_id.external_referential_id.id',
                                  'defaults': 'log.origin_defaults',
                                  'context': 'log.origin_context',
                                  },
                    }
        }
        return mapping


osv.osv.read_w_order = read_w_order
osv.osv.browse_w_order = browse_w_order
osv.osv.prefixed_id = prefixed_id
osv.osv.id_from_prefixed_id = id_from_prefixed_id
osv.osv.get_last_imported_external_id = get_last_imported_external_id
osv.osv.get_modified_ids = get_modified_ids
osv.osv.external_connection = external_connection
osv.osv.oeid_to_extid = oeid_to_extid
osv.osv.extid_to_existing_oeid = extid_to_existing_oeid
osv.osv.extid_to_oeid = extid_to_oeid
osv.osv.oevals_from_extdata = oevals_from_extdata
osv.osv.get_external_data = get_external_data
osv.osv.import_with_try = import_with_try
osv.osv.ext_import = ext_import
osv.osv.retry_import = retry_import
osv.osv.oe_update = oe_update
osv.osv.oe_create = oe_create
osv.osv.extdata_from_oevals = extdata_from_oevals
osv.osv.ext_export = ext_export
osv.osv.retry_export = retry_export
osv.osv.can_create_on_update_failure = can_create_on_update_failure
osv.osv.ext_create = ext_create
osv.osv.try_ext_update = try_ext_update
osv.osv.ext_update = ext_update
osv.osv.report_action_mapping = report_action_mapping
osv.osv._prepare_external_id_vals = _prepare_external_id_vals
osv.osv._search_existing_id_by_vals = _search_existing_id_by_vals

