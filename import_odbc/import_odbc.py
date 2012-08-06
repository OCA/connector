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

import os
import sys
import datetime
from osv import fields, osv

import logging
_logger = logging.getLogger(__name__)

class import_odbc_dbsource(osv.osv):
    _name = "base.external.dbsource"
    _inherit = "base.external.dbsource"

    _columns = {
        'dbtable_ids': fields.one2many('import.odbc.dbtable', 'dbsource_id', 'Import tables'),
    }

    def import_run(self, cr, uid, ids, context=None):
        #Prepare objects to be used
        table_obj = self.pool.get('import.odbc.dbtable')
        #Import each selected dbsource
        data = self.browse(cr, uid, ids)
        for obj in data:
            #Get list of tables
            table_ids = [x.id for x in obj.dbtable_ids]
            #Run import
            table_obj.import_run( cr, uid, table_ids)
        return True
    
import_odbc_dbsource()

class import_odbc_dbtable(osv.osv):
    _name="import.odbc.dbtable"
    _description = 'Import Table Data'
    _order = 'exec_order'
    _columns = {
        'name': fields.char('Datasource name', required=True, size=64),
        'enabled': fields.boolean('Execution enabled'),
        'dbsource_id': fields.many2one('base.external.dbsource', 'Database source', required=True),
        'sql_source': fields.text('SQL', required=True, help='Column names must be valid "import_data" columns.'),
        'model_target': fields.many2one('ir.model','Target object'),
        'noupdate': fields.boolean('No updates', help="Only create new records; disable updates to existing records."),
        'exec_order': fields.integer('Execution order', help="Defines the order to perform the import"),
        'last_sync': fields.datetime('Last sync date', help="Datetime for the last succesfull sync. Later changes on the source may not be replicated on the destination"),
        'start_run': fields.datetime('Time started', readonly=True),
        'last_run': fields.datetime('Time ended', readonly=True),
        'last_record_count': fields.integer('Last record count', readonly=True),
        'last_error_count': fields.integer('Last error count', readonly=True),
        'last_warn_count': fields.integer('Last warning count', readonly=True),
        'last_log': fields.text('Last run log', readonly=True),
        'ignore_rel_errors': fields.boolean('Ignore relationship errors', 
            help="On error try to reimport rows ignoring relationships."),
        'raise_import_errors': fields.boolean('Raise import errors', 
            help="Import errors not handled, intended for debugging purposes."),
    }
    _defaults = {
        'enabled': True,
        'exec_order': 10,
    }

    #TODO: allow differnt cron jobs to run different sets of imports
    #TODO: add field for user-friendly error report, to be used in automatic e-mail
    #TODO: create a "clean-up" procedure, to act on (inactivate?) each record without correspondence in the SQL results 
    #TODO: write dates in dbtable in UTC
    
    def import_run(self, cr, uid, ids=None, context=None):
        #TODO: refactor - split in smaller routines!
        def is_id_field(x): 
            """"Detect is the column is a one2many field"""
            return len(x)>3 and x[-3:] == ':id' or x[-3:] == '/id'
            
        def remove_cols(ids, cols, data):
            """Remove ids cols and data lists"""
            rc, rd = list(), list()
            for c, d in zip(cols, data):
                if c not in ids:
                    rc.append(c)
                    rd.append(d)
            return rc, rd
        
        def safe_import(cr, uid, target_obj, colrow, datarows, noupdate, raise_import_errors=False):
            """Import data and returns error msg or empty string"""
            res = ''
            if raise_import_errors:
                target_obj.import_data(cr, uid, colrow, datarows, noupdate=obj.noupdate)
            else:
                try:
                    target_obj.import_data(cr, uid, colrow, datarows, noupdate=obj.noupdate)
                    cr.commit()
                except:
                    #Can't use cr.rollback() - it breaks ir.cron's lock on the job, causing duplicate spawns
                    res = str(sys.exc_info()[1])
            return res

        def text_to_log(level, obj_id = '', msg = '', rel_id = ''):
            if '_id_' in obj_id:
                obj_id = '.'.join(obj_id.split('_')[:-2]) \
                       + ': ' + obj_id.split('_')[-1]
            if ': .' in msg and not rel_id:
                rel_id = msg[msg.find(': .')+3:]
                if '_id_' in rel_id:
                    rel_id = '.'.join(rel_id.split('_')[:-2]) \
                           + ': ' + rel_id.split('_')[-1]
                    msg = msg[:msg.find(': .')]
            return '%s|%s\t|%s\t|%s' % (level.ljust(5), obj_id, rel_id, msg)
            
        #Prepare support objects
        dbsource_obj = self.pool.get('base.external.dbsource')
        ###_logger.setLevel(logging.DEBUG)
        _logger.debug('Import job STARTING...')
        #Build id list if none is provided
        if not ids:
            ids = self.search(cr, uid, [('enabled', '=', True)])
        #Sort list by exec_order
        actions = self.read(cr, uid, ids, ['id', 'exec_order'])
        actions.sort(key = lambda x:(x['exec_order'], x['id']))
        #Consider each dbtable:
        for action in actions:
            obj = self.browse(cr, uid, action['id'])
            #Skip if it's inactive or is running
            if obj.enabled:
                #Prepare log to write
                #now() microseconds are stripped to avoid problem with SQL smalldate
                #TODO: convert UTC Now to local timezone (http://stackoverflow.com/questions/4770297/python-convert-utc-datetime-string-to-local-datetime)
                _logger.debug('Importing %s...' % obj.name)
                log = { 
                    'start_run': datetime.datetime.now().replace(microsecond=0),
                    'last_run': None,
                    'last_record_count': 0,
                    'last_error_count': 0,
                    'last_warn_count': 0,
                    'last_log': ''
                    }
                self.write(cr, uid, [obj.id], log)
                log_lines = list()
                ignore_rel_errors = obj.ignore_rel_errors
                raise_import_errors = obj.raise_import_errors
                #Prepare SQL sentence; replace every "?" with the last_sync date
                sql = obj.sql_source
                dt  = obj.last_sync
                params = tuple( [dt] * sql.count('?') )
                #Open the source connection
                conn = dbsource_obj.conn_open(cr, uid, obj.dbsource_id.id)
                #Get source data cursor
                db_cursor = conn.cursor()
                db_cursor.execute(sql, params)
                #Build column list from cursor:
                # - exclude columns titled "None"
                # - add an extra "id" for the xml_id
                cols = [x[0] for x in db_cursor.description if x[0].upper() != 'NONE']
                cols.append('id')
                #Get destination object
                model = obj.model_target.model
                model_obj = self.pool.get(model)
                #Setup prefix to use in xml_ids 
                xml_prefix = model.replace('.', '_') + "_id_"
                #Import each row:
                for row in db_cursor:
                    #Build data row; import only columns present in the "cols" list
                    datarow = []
                    for (i, col) in enumerate(row):
                        if db_cursor.description[i][0] in cols:
                            ###print '==', db_cursor.description[i][0], col
                            ###colstr = unicode(str(col).strip(), errors='replace').encode('utf-8')
                            ###print str(colstr)
                            colstr = str(col).strip()
                            ###print colstr
                            ###if col == 'Ind\xfastria':
                            ###    col = u'JOS\xc9'
                            ###    colstr=col
                            ###import pdb; pdb.set_trace()
                            datarow.append( colstr )
                            #TODO: Handle datetimes properly - convert from localtime to UTC!
                    #Add "xml_id" column to row
                    datarow.append( xml_prefix + str(row[0]).strip() )
                    _logger.debug( datarow )
                    #Import the row; on error, write line to the log
                    log['last_record_count'] += 1
                    err = safe_import(cr, uid, model_obj, cols, [datarow], obj.noupdate, raise_import_errors)
                    #If error; retry ignoring many2one fields...
                    if err and ignore_rel_errors:
                        #Log a warning
                        log_lines.append( text_to_log('WARN', datarow[-1], err ) )
                        log['last_warn_count'] += 1
                        #Try ignoring each many2one (tip: in the SQL sentence select more problematic FKs first)
                        idcols = filter(is_id_field, cols)
                        for idcol in idcols:
                            c, d = remove_cols( [idcol], cols, datarow)
                            err = safe_import(cr, uid, c, [d], obj.noupdate, raise_import_errors)
                            if not err: 
                                break
                        #If still error; retry ignoring all ".../id" fields
                        if err:
                            c, d = remove_cols( idcols, cols, datarow)
                            err = safe_import(cr, uid, c, [d], obj.noupdate, raise_import_errors)
                    #If still error after all import tries, reject data row
                    if err:
                        log_lines.append( text_to_log('ERROR', datarow[-1], err ) )
                        log['last_error_count'] += 1
                    #Inform progress on long Imports, every 500 rows
                    if log['last_record_count'] % 500 == 0:
                        _logger.info('...%s rows processed...' % (log['last_record_count']) )

                #Finished importing all rows
                msg = 'Imported %s , %s rows, %s errors, %s warnings.' % (
                    model, 
                    log['last_record_count'], 
                    log['last_error_count'] ,
                    log['last_warn_count'] ) 
                #Close the connection
                conn.close()
                #If no errors, write new sync date
                if not (log['last_error_count'] or log['last_warn_count']):
                    log['last_sync'] = log['start_run']
                level = logging.DEBUG
                if log['last_warn_count']: level = logging.WARN
                if log['last_error_count']: level = logging.ERROR
                _logger.log(level, msg)
                #Write run log, either if the table import is active or inactive
                if log_lines:
                     log_lines.insert(0, text_to_log('LEVEL', '== Line ==    ','== Relationship ==','== Message =='))
                     log.update( {'last_log': '\n'.join(log_lines)} )
                log.update({ 'last_run': datetime.datetime.now().replace(microsecond=0) }) #second=0, 
                self.write(cr, uid, [obj.id], log)
                #cr.commit() #Avoid conflicts with user actions on long running imports (?)
        #Finished
        _logger.debug('Import job FINISHED.')
        return True

    def import_schedule(self, cr, uid, ids, context=None):
        cron_obj = self.pool.get('ir.cron')
        new_create_id = cron_obj.create(cr, uid, {
            'name': 'Import ODBC tables',
            'interval_type': 'hours',
            'interval_number': 1, 
            'numbercall': -1,
            'model': 'import.odbc.dbtable',
            'function': 'import_run', 
            'doall': False,
            'active': True
            })
        return {
            'name': 'Import ODBC tables',
            'view_type': 'form',
            'view_mode': 'form,tree',
            'res_model': 'ir.cron',
            'res_id': new_create_id,
            'type': 'ir.actions.act_window',
            }
        
import_odbc_dbtable()
