# -*- encoding: utf-8 -*-
###############################################################################
#                                                                             #
#   base_external_referentials for OpenERP                                    #
#   Copyright (C) 2011 Akretion Sébastien BEAU <sebastien.beau@akretion.com>  #
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

from openerp.osv.osv import except_osv
import pooler
from tools.translate import _
from message_error import MappingError
import functools
import xmlrpclib
from openerp.tools.config import config

#TODO refactor me we should create 2 decorator
# 1 only_for_referential
# 2 only_for_referential_category
def only_for_referential(ref_type=None, ref_categ=None, super_function=None):
    """
    This decorator will execute the code of the function decorated only if
    the referential_type match with the referential_type pass in the context
    If not super method will be call.
    argument must be the referential or the referential_id or the external_session
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapped(self, cr, uid, argument, *args, **kwargs):
            if self._name == 'external.referential' and (isinstance(argument, list) or isinstance(argument, int)):
                referential_id = isinstance(argument, list) and argument[0] or argument
                referential = self.browse(cr, uid, referential_id)
            else:
                referential = argument.referential_id
            if ref_type and referential.type_id.name.lower() == ref_type.lower() or ref_categ and referential.categ_id.name.lower() == ref_categ.lower():
                return func(self, cr, uid, argument, *args, **kwargs)
            else:
                if super_function:
                    return super_function(self, cr, uid, argument, *args, **kwargs)
                else:
                    name = func.__name__
                    use_next_class = False
                    for base in self.__class__.mro()[1:]:
                        if use_next_class and hasattr(base, name):
                            return getattr(base, name)(self, cr, uid, argument, *args, **kwargs)
                        class_func = base.__dict__.get(name)
                        if class_func:
                            original_func = class_func.__dict__.get("_original_func_before_wrap")
                            if original_func is func:
                                use_next_class = True
                    raise except_osv(_("Not Implemented"), _("No parent method found"))
        wrapped._original_func_before_wrap = func
        return wrapped
    return decorator


def open_report(func):
    """ This decorator will start and close a report for the function call
    The function must start with "self, cr, uid, object"
    And the object must have a field call "referential_id" related to the object "external.referential"
    """
    @functools.wraps(func)
    def wrapper(self, cr, uid, external_session, *args, **kwargs):
        #if not self._columns.get('referential_id'):
        #    raise except_osv(_("Not Implemented"), _("The field referential_id doesn't exist on the object %s. Reporting system can not be used" %(self._name,)))

        report_obj = self.pool.get('external.report')
        context = kwargs.get('context')
        if context is None:
            context={}
            kwargs['context'] = context

        #Start the report
        report_id = report_obj.start_report(cr, uid, external_session, id=None, action=func.__name__, action_on=self._name, context=context)

        #Execute the original function and add the report_id to the context
        context['report_id'] = report_id
        response = func(self, cr, uid, external_session, *args, **kwargs)

        #Close the report
        report_obj.end_report(cr, uid, external_session, report_id, context=context)

        return response
    return wrapper


def catch_error_in_report(func):
    """ This decorator open and close a new cursor and if an error occure it will generate a error line in the reporting system
    The function must start with "self, cr, uid, object"
    And the object must have a field call "referential_id" related to the object "external.referential"
    """
    @functools.wraps(func)
    def wrapper(self, cr, uid, external_session, resource, *args, **kwargs):
        context = kwargs.get('context')
        if not (context and context.get('report_id')):
            external_session.logger.debug(_("There is no key report_id in the context, error will be not catch"))
            return func(self, cr, uid, external_session, resource, *args, **kwargs)
        if context.get('report_line_based_on'):
            if not context['report_line_based_on'] == self._name:
                return func(self, cr, uid, external_session, resource, *args, **kwargs)
        report_line_obj = self.pool.get('external.report.line')
        report_line_id = report_line_obj.start_log(
                                    cr,
                                    uid,
                                    self._name,
                                    func.__name__,
                                    #TODO manage external id and res_id in a good way
                                    external_id=context.get('external_id_key_for_report') and resource.get(context.get('external_id_key_for_report')),
                                    res_id= not context.get('external_id_key_for_report') and args and args[0],
                                    resource=resource,
                                    args = args,
                                    kwargs = kwargs,
                            )
        import_cr = pooler.get_db(cr.dbname).cursor()
        response = False
        try:
            response = func(self, import_cr, uid, external_session, resource, *args, **kwargs)
        except MappingError as e:
            if config['debug_mode']: raise
            import_cr.rollback()
            error_message = 'Error with the mapping : %s. Error details : %s'%(e.mapping_name, e.value),
            report_line_obj.log_fail(cr, uid, external_session, report_line_id, error_message, context=context)
        except xmlrpclib.Fault as e:
            if config['debug_mode']: raise
            import_cr.rollback()
            error_message = 'Error with xmlrpc protocole. Error details : error %s : %s'%(e.faultCode, e.faultString)
            report_line_obj.log_fail(cr, uid, external_session, report_line_id, error_message, context=context)
        except except_osv as e:
            if config['debug_mode']: raise
            import_cr.rollback()
            error_message = '%s : %s'%(e.name, e.value)
            report_line_obj.log_fail(cr, uid, external_session, report_line_id, error_message, context=context)
        except Exception as e:
            if config['debug_mode']: raise
            #TODO write correctly the message in the report
            import_cr.rollback()
            error_message = str(e)
            report_line_obj.log_fail(cr, uid, external_session, report_line_id, error_message, context=context)
        else:
            report_line_obj.log_success(cr, uid, external_session, report_line_id, context=context)
            import_cr.commit()
        finally:
            import_cr.close()
        return response
    return wrapper

#This decorator is for now a prototype it will be improve latter, maybe the best will to have two kind of decorator (import and export)
def catch_action(func):
    """ This decorator open and close a new cursor and if an error occure it will generate a error line in the reporting system
    The function must start with "self, cr, uid, object_id"
    And the object must have a field call "referential_id" related to the object "external.referential"
    """
    @functools.wraps(func)
    def wrapper(self, cr, uid, *args, **kwargs):
        context = kwargs.get('context', {})
        report_line_obj = self.pool.get('external.report.line')
        report_line_id = report_line_obj.start_log(
                                    cr,
                                    uid,
                                    self._name,
                                    func.__name__,
                                    res_id= args[0],
                                    args = args,
                                    kwargs = kwargs,
                            )
        import_cr = pooler.get_db(cr.dbname).cursor()
        response = False
        try:
            response = func(self, import_cr, uid, *args, **kwargs)
        except MappingError as e:
            if config['debug_mode']: raise
            import_cr.rollback()
            error_message = 'Error with the mapping : %s. Error details : %s'%(e.mapping_name, e.value),
            report_line_obj.log_fail(cr, uid, None, report_line_id, error_message, context=context)
        except xmlrpclib.Fault as e:
            if config['debug_mode']: raise
            import_cr.rollback()
            error_message = 'Error with xmlrpc protocole. Error details : error %s : %s'%(e.faultCode, e.faultString)
            report_line_obj.log_fail(cr, uid, None, report_line_id, error_message, context=context)
        except except_osv as e:
            if config['debug_mode']: raise
            import_cr.rollback()
            error_message = '%s : %s'%(e.name, e.value)
            report_line_obj.log_fail(cr, uid, None, report_line_id, error_message, context=context)
        except Exception as e:
            if config['debug_mode']: raise
            #TODO write correctly the message in the report
            import_cr.rollback()
            error_message = str(e)
            report_line_obj.log_fail(cr, uid, None, report_line_id, error_message, context=context)
        else:
            report_line_obj.log_success(cr, uid, None, report_line_id, context=context)
            import_cr.commit()
        finally:
            import_cr.close()
        return response
    return wrapper



def commit_now(func):
    """ This decorator open and close a new cursor and if an error occure it raise an error
    The function must start with "self, cr"
    """
    @functools.wraps(func)
    def wrapper(self, cr, *args, **kwargs):
        new_cr = pooler.get_db(cr.dbname).cursor()
        try:
            response = func(self, new_cr, *args, **kwargs)
        except:
            new_cr.rollback()
            raise
        else:
            new_cr.commit()
        finally:
            new_cr.close()
        return response
    return wrapper


