# -*- coding: utf-8 -*-
##############################################################################
#
#    jasper_server module for OpenERP,
#    Copyright (C) 2009-2011 SYLEAM Info Services (<http://www.syleam.fr/>)
#                            Christophe CHAUVET
#
#    This file is a part of jasper_server
#
#    jasper_server is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    jasper_server is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

# from openerp.osv import osv
from openerp.osv import orm
from openerp.osv import fields
from openerp.tools import ustr
from openerp.tools.translate import _
from openerp.modules import get_module_path
import openerp
import time
import os
import jasperlib
import ast

from openerp.osv.orm import browse_null

from lxml.etree import Element, SubElement, tostring
from openerp.addons.jasper_server.report.report_exception import EvalError

from openerp.osv.fields import float as float_field, function as function_field, datetime as datetime_field
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
from datetime import datetime

def get_date_length(date_format=DEFAULT_SERVER_DATE_FORMAT):
    return len((datetime.now()).strftime(date_format))

import logging
_logger = logging.getLogger(__name__)


def log_error(message):
    _logger.error(message)


class JasperServer(orm.Model):
    """
    Class to store the Jasper Server configuration
    """
    _name = 'jasper.server'
    _description = 'Jasper server configuration'
    _rec_name = 'host'

    _columns = {
        'host': fields.char('Host', size=128, required=True,
                            help='Enter hostname or IP address'),
        'port': fields.integer('Port'),
        'user': fields.char('Username', size=128,
                            help='Enter the username for JasperServer user, by default is jasperadmin'),  # noqa
        'pass': fields.char('Password', size=128,
                            help='Enter the password for the user, by defaul is jasperadmin'),  # noqa
        'repo': fields.char('Repository', size=256, required=True,
                            help='Enter the address of the repository'),
        'sequence': fields.integer('Sequence'),
        'enable': fields.boolean('Enable',
                                 help='Check this, if the server is available',),  # noqa
        'status': fields.char('Status', size=64,
                              help='Check the registered and authentification status'),  # noqa
        'prefix': fields.char('Prefix', size=32,
                              help='If prefix is filled, the reportUnit must in the new tree, usefull on a share hosting'),  # noqa
    }

    _defaults = {
        'host': 'localhost',
        'port': 8080,
        'user': 'jasperadmin',
        'pass': 'jasperadmin',
        'repo': '/jasperserver/services/repository',
        'sequence': 10,
        'prefix': False,
    }

    def check_auth(self, cr, uid, ids, context=None):
        """
        Check if we can join the JasperServer instance,
        send the authentification and check the result
        """
        js_config = self.read(cr, uid, ids[0], context=context)
        try:
            js = jasperlib.Jasper(host=js_config['host'],
                                  port=js_config['port'],
                                  user=js_config['user'],
                                  pwd=js_config['pass'])
            js.auth()
        except jasperlib.ServerNotFound:
            message = _('Error, JasperServer not found at %s (port: %d)') % (js.host, js.port)  # noqa
            _logger.error(message)
            return self.write(cr, uid, ids, {'status': message},
                              context=context)
        except jasperlib.AuthError:
            message = _('Error, JasperServer authentification failed for user %s/%s') % (js.user, js.pwd)  # noqa
            _logger.error(message)
            return self.write(cr, uid, ids, {'status': message},
                              context=context)

        return self.write(cr, uid, ids,
                          {'status': _('JasperServer Connection OK')},
                          context=context)

    @staticmethod
    def format_element(element):
        """
        convert element in lowercase and replace space per _
        """
        return ustr(element).lower().replace(' ', '_')

    def generate_context(self, cr, uid, context=None):
        """
        generate xml with context header
        """
        f_list = (
            'context_tz', 'context_lang', 'name', 'signature', 'company_id',
        )

        # TODO: Use browse to add the address of the company
        user = self.pool.get('res.users')
        usr = user.read(cr, uid, [uid], context=context)[0]
        ctx = Element('context')

        for val in usr:
            if val in f_list:
                e = Element(val)
                if usr[val]:
                    if isinstance(usr[val], list):
                        e.set('id', str(usr[val][0]))
                        e.text = str(usr[val][1])
                    else:
                        e.text = str(usr[val])
                ctx.append(e)

        return ctx

    def generate_xml(self, cr, uid, relation, id, depth, old_relation='',
                     old_field='', context=None):
        """
        Generate xml for an object recursively
        """
        if not context:
            context = {}
        irm = self.pool.get('ir.model')
        if isinstance(relation, int):
            irm_ids = [relation]
        else:
            irm_ids = irm.search(cr, uid, [('model', '=', relation)])

        if not irm_ids:
            log_error('Model %s not found !' % relation)

        # #
        # We must ban many model
        #
        ban = (
            'res.company', 'ir.model', 'ir.model.fields', 'res.groups',
            'ir.model.data', 'ir.model.grid', 'ir.model.access', 'ir.ui.menu',
            'ir.actions.act_window', 'ir.action.wizard', 'ir.attachment',
            'ir.cron', 'ir.rule', 'ir.rule.group', 'ir.actions.actions',
            'ir.actions.report.custom', 'ir.actions.report.xml',
            'ir.actions.url', 'ir.ui.view', 'ir.sequence',
        )

        ##
        # If generate_xml was called by a relation field, we must keep
        # the original filename
        ir_model = irm.read(cr, uid, irm_ids[0])
        if isinstance(relation, int):
            relation = ir_model['model']

        irm_name = self.format_element(ir_model['name'])
        if old_field:
            x = Element(self.format_element(old_field), relation=relation,
                        id=str(id))
        else:
            x = Element(irm_name, id='%s' % id)

        if not id:
            return x

        if isinstance(id, (int, long)):
            id = [id]

        obj = self.pool.get(relation)
        mod_ids = obj.read(cr, uid, id, context=context)
        mod_fields = obj.fields_get(cr, uid)
        for mod in mod_ids:
            for f in mod_fields:
                field = f.lower()
                name = mod_fields[f]['string']
                type = mod_fields[f]['type']
                value = mod[f]
                e = Element(field, label='%s' % self.format_element(name))
                if type in ('char', 'text', 'selection', 'html'):
                    e.text = value and unicode(value) or ''
                elif type == 'integer':
                    e .text = value and str(value) or '0'
                elif type == 'float':
                    e.text = value and str(value) or '0.0'
                elif type == 'date':
                    e.set('format', 'YYYY-mm-dd')
                    e.text = value or ''
                elif type == 'datetime':
                    e.set('format', 'YYYY-mm-dd HH:MM:SS')
                    e.text = value or ''
                elif type == 'boolean':
                    e.text = str(value)
                elif type == 'many2one':
                    if not isinstance(value, int):
                        value = value and value[0] or 0
                    # log_error('Current: %r Old: %r' % (mod_fields[f]['relation'], relation))
                    if depth > 0 and value and mod_fields[f]['relation'] != old_relation and mod_fields[f]['relation'] not in ban:
                        e = self.generate_xml(cr, uid, mod_fields[f]['relation'], value, depth - 1, relation, field)
                    else:
                        e.set('id', '%r' % value or 0)
                        if not isinstance(value, int):
                            e.text = str(mod[f][1])
                elif type in ('one2many', 'many2many'):
                    if depth > 0 and value and \
                       mod_fields[f]['relation'] not in ban:
                        for v in value:
                            x.append(self.generate_xml(
                                cr, uid, mod_fields[f]['relation'], v,
                                depth - 1, relation, field))
                        continue
                    else:
                        e.set('id', '%r' % value)
                elif type in ('binary', 'reference'):
                    e.text = 'Not supported'
                else:
                    log_error('OUPS un oubli %s: %s(%s)' % (field, name, type))
                x.append(e)
        return x

    def generatorYAML(self, cr, uid, jasper_document, current_object, user_company, user, context=None):

        import yaml
        root = Element('data')

        ctx = context.copy()
        for yaml_object in jasper_document.yaml_object_ids:

            model_obj = self.pool.get(yaml_object.model.model)
            user_id = uid
            if yaml_object.user_id.id:
                user_id = yaml_object.user_id.id
            if yaml_object.context:
                yaml_context = ast.literal_eval( yaml_object.context)
                
                for key,value in yaml_context.items():
                    ctx[key] = value
            aux = yaml_object.domain
            my_args = []
            if aux:
                aux = aux.replace('[[', '').replace(']]', '')
                my_args = eval(aux, {'o': current_object, 'c': user_company, 't': time, 'u': user}) or ''
            model_ids = model_obj.search(cr, user_id,
                                         args=my_args,
                                         offset=yaml_object.offset,
                                         limit=yaml_object.limit if yaml_object.limit > 0 else None,
                                         order=yaml_object.order,
                                         context=ctx)

            xmlObject = Element('object')        
            xmlObject.set("name", yaml_object.name)
            xmlObject.set("model", yaml_object.model.name)

            # If add_super_container, we have to add a main container to gather other child containers, one per item.
            # This will allow to create a single report iterating over items as lines, instead of a different report per item
            if jasper_document.add_super_container:
                parent = SubElement(xmlObject, 'container')
            else:
                parent = xmlObject

            for object in model_obj.browse(cr, user_id, model_ids, ctx):
                xmlField = Element('container')

                # take the field name if it exists in model and if name is not False
                # else take the rec_name value if a rec_name was used
                # else take simply the object id

                if 'name' in object._fields and object.name:
                    xmlField.set("name", object.name)
                elif object._rec_name != None:
                    rec_name_value = model_obj.read(cr, uid,
                                                    [object.id],
                                                    [object._rec_name])[0][object._rec_name]
                    if rec_name_value:
                        xmlField.set("name", rec_name_value)
                    else:
                        xmlField.set("name", str(object.id))
                else:
                    xmlField.set("name", str(object.id))
                try:
                    self.generate_from_yaml(cr, user_id, xmlField, object, yaml.load(yaml_object.fields), context=ctx)
                except:
                    raise
                parent.append(xmlField)

            if jasper_document.add_super_container:
                xmlObject.append(parent)

            root.append(xmlObject)

        return tostring(root, pretty_print=ctx.get('indent', False))


    def generate_from_yaml(self, cr, uid, root, object, fields, prefix='', context=None):
        """
        Generate xml for an object recursively
        """

        if prefix:
            prefix = prefix + '_'

        for field in fields:
            xmlField = Element("DummyInitialisation")

            if type(field) is dict:
                fieldname = field.keys()[0]
                value = field.values()[0]
                xmlField = Element(prefix + fieldname)

                if object._model._all_columns[fieldname].column._type in ['one2many','many2many']:  # o2m, m2m
                    for objectListElement in object[fieldname]:
                        xmlContainerField = Element("container")
                        xmlContainerField.set("name", fieldname)
                        self.generate_from_yaml(cr, uid, xmlContainerField, objectListElement, value, prefix + fieldname, context=context)

                        xmlField.append(xmlContainerField)
                elif object._model._all_columns[fieldname].column._type == 'many2one':  # m2o
                    if not isinstance(object[fieldname], browse_null):
                        self.generate_from_yaml(cr, uid, xmlField, object[fieldname], value, prefix + fieldname, context=context)
                else:
                    # set element content
                    xmlField.text = self._format_element(xmlField, object._model._fields[field].type, object[fieldname])
                    #xmlField.text = self._format_and_translate_element(cr, uid, xmlField, object._model._fields[field].type, object[fieldname], context=context)

            else:
                xmlField = Element(prefix + field)

                # set element content
                xmlField.text = ''
                if object:
                    xmlField.text = self._format_element(xmlField, object._model._fields[field].type, object[field])
                    #xmlField.text = self._format_and_translate_element(cr, uid, xmlField, object._model._fields[field].type, object[field], context=context)


            root.append(xmlField)
        return

    def get_digits(self, obj=None, f=None, dp=None):
        d = DEFAULT_DIGITS = 2
        if dp:
            decimal_precision_obj = self.pool['decimal.precision']
            d = decimal_precision_obj.precision_get(self.cr, self.uid, dp)
        elif obj and f:
            res_digits = getattr(obj._columns[f], 'digits', lambda x: ((16, DEFAULT_DIGITS)))
            if isinstance(res_digits, tuple):
                d = res_digits[1]
            else:
                d = res_digits(self.cr)[1]
        elif (hasattr(obj, '_field') and\
                isinstance(obj._field, (float_field, function_field)) and\
                obj._field.digits):
                d = obj._field.digits[1]
                if not d and d is not 0:
                    d = DEFAULT_DIGITS
        return d

    def formatLang(self, cr, uid, value, digits=None, date=False, date_time=False, grouping=True, monetary=False, dp=False, currency_obj=False, language='en_US'):
        """
            Assuming 'Account' decimal.precision=3:
                formatLang(value) -> digits=2 (default)
                formatLang(value, digits=4) -> digits=4
                formatLang(value, dp='Account') -> digits=3
                formatLang(value, digits=5, dp='Account') -> digits=5
        """
        if digits is None:
            if dp:
                digits = self.get_digits(dp=dp)
            else:
                digits = self.get_digits(value)

        if isinstance(value, (str, unicode)) and not value:
            return ''

        lang_pool = self.pool.get('res.lang')
        lang_id = lang_pool.search(cr, uid, [('code', '=', language)])
        lang_obj = lang_pool.browse(cr, uid, lang_id)
        lang_dict = {}
        lang_dict.update({'lang_obj': lang_obj, 'date_format': lang_obj.date_format, 'time_format': lang_obj.time_format})

        if date or date_time:
            if not value:
                return ''

            date_format = lang_dict['date_format']
            parse_format = DEFAULT_SERVER_DATE_FORMAT
            if date_time:
                value = value.split('.')[0]
                date_format = date_format + " " + lang_dict['time_format']
                parse_format = DEFAULT_SERVER_DATETIME_FORMAT
            if isinstance(value, basestring):
                # FIXME: the trimming is probably unreliable if format includes day/month names
                #        and those would need to be translated anyway.
                date = datetime.strptime(value[:get_date_length(parse_format)], parse_format)
            elif isinstance(value, time.struct_time):
                date = datetime(*value[:6])
            else:
                date = datetime(*value.timetuple()[:6])
            if date_time:
                # Convert datetime values to the expected client/context timezone
                date = datetime_field.context_timestamp(self.cr, self.uid,
                                                        timestamp=date,
                                                        context=self.localcontext)
            return date.strftime(date_format.encode('utf-8'))

        res = lang_dict['lang_obj'].format('%.' + str(digits) + 'f', value, grouping=grouping, monetary=monetary)
        if currency_obj:
            if currency_obj.position == 'after':
                res = u'%s\N{NO-BREAK SPACE}%s' % (res, currency_obj.symbol)
            elif currency_obj and currency_obj.position == 'before':
                res = u'%s\N{NO-BREAK SPACE}%s' % (currency_obj.symbol, res)
        return res

    def _format_and_translate_element(self, cr, uid, element, field_type, field_value, context=None):

        language = context.get('lang', False)

        if field_type in ('char', 'text', 'selection', 'html'):
            return field_value and unicode(field_value) or ''
        elif field_type == 'integer':
            return field_value and str(field_value) or '0'
        elif field_type == 'float':
            # Float is already given with the separators and format of the language
            value = field_value or 0.0
            return self.formatLang(cr, uid, value, grouping=True, language=language)
        elif field_type == 'date':
            # Date is already given with the separators and format of the language
            return self.formatLang(cr, uid, field_value, date=True, language=language)
        elif field_type == 'datetime':
            # Datetime is already given with the separators and format of the language
            return self.formatLang(cr, uid, field_value, datetime=True, language=language)
        elif field_type == 'boolean':
            return str(field_value)
        elif field_type == 'many2one':
            raise EvalError(_('Many2One'), _('You cannot use many2one directly.\n\nDefine subelement for: "%s"') % str(element.tag))
        elif field_type in ('binary', 'reference'):
            if field_value:
                return str(field_value)
            else:
                return ''
        else:
            log_error('OUPS un oubli %s: %s(%s)' % (field_type, element, field_value))


    def _format_element(self, element, field_type, field_value):

        if field_type in ('char', 'text', 'selection', 'html'):
            return field_value and unicode(field_value) or ''
        elif field_type == 'integer':
            return field_value and str(field_value) or '0'
        elif field_type == 'float':
            return field_value and str(field_value) or '0.0'
        elif field_type == 'date':
            element.set('format', 'yyyy-MM-dd HH:mm:ss')
            if field_value:
                return field_value + ' 00:00:00' or ''
            else:
                return ''
        elif field_type == 'datetime':
            element.set('format', 'yyyy-MM-dd HH:mm:ss')
            return field_value or ''
        elif field_type == 'boolean':
            return str(field_value)
        elif field_type == 'many2one':
            raise EvalError(_('Many2One'), _('You cannot use many2one directly.\n\nDefine subelement for: "%s"') % str(element.tag))
        elif field_type in ('binary', 'reference'):
            if field_value:
                return str(field_value)
            else:
                return ''
        else:
            log_error('OUPS un oubli %s: %s(%s)' % (field_type, element, field_value))

    def generator(self, cr, uid, model, id, depth, context=None):
        root = Element('data')
        root.append(self.generate_context(cr, uid, context=context))
        root.append(self.generate_xml(cr, uid, model, id, depth,
                                      context=context))
        return tostring(root, pretty_print=context.get('indent', False))


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
