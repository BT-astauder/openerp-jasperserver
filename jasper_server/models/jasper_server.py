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

from odoo import api, fields, models
from odoo.tools import ustr
from odoo import _
import time
from odoo.addons.jasper_server.common import jasperlib
from ast import literal_eval

from lxml.etree import Element, tostring
from odoo.addons.jasper_server.report.report_exception import EvalError

import logging
_logger = logging.getLogger(__name__)


class JasperServer(models.Model):
    """
    Class to store the Jasper Server configuration
    """
    _name = 'jasper.server'
    _description = 'Jasper server configuration'
    _rec_name = 'host'

    host = fields.Char('Host', size=128, required=True, default='localhost',
                       help='Enter hostname or IP address')
    port = fields.Integer('Port', default=8080)
    user = fields.Char('Username', size=128, default='jasperadmin',
                       help='Enter the username for JasperServer user, by default is jasperadmin')
    password = fields.Char('Password', size=128, default='jasperadmin', oldname='pass',
                           help='Enter the password for the user, by default is jasperadmin')
    repo = fields.Char('Repository', size=256, required=True, default='/jasperserver/services/repository',
                       help='Enter the address of the repository')
    sequence = fields.Integer('Sequence', default=10)
    enable = fields.Boolean('Enable',
                            help='Check this, if the server is available')
    status = fields.Char('Status', size=64,
                         help='Check the registered and authentication status')
    prefix = fields.Char('Prefix', size=32, default=False,
                         help='If prefix is filled, the reportUnit must in the new tree, usefull on a share hosting')

    @api.multi
    def check_auth(self):
        """
        Check if we can join the JasperServer instance,
        send the authentication and check the result
        """
        self.ensure_one()
        try:
            js = jasperlib.Jasper(host=self.host,
                                  port=self.port,
                                  user=self.user,
                                  pwd=self.password)
            js.auth()
            message = _('JasperServer Connection OK')
        except jasperlib.ServerNotFound:
            message = _('Error, JasperServer not found at %s (port: %d)') % (js.host, js.port)  # noqa
            _logger.error(message)
        except jasperlib.AuthError:
            message = _('Error, JasperServer authentication failed for user %s/%s') % (js.user, js.pwd)  # noqa
            _logger.error(message)

        self.status = message
        return

    @staticmethod
    def format_element(element):
        """
        convert element in lowercase and replace space per _
        """
        return ustr(element).lower().replace(' ', '_')

    @api.model
    def generate_context(self):
        """
        generate xml with context header
        """
        f_list = (
            'context_tz', 'context_lang', 'name', 'signature', 'company_id',
        )

        # TODO: Use browse to add the address of the company
        usr = self.env.user.read()
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

    @api.model
    def generate_xml(self, relation, object_id, depth, old_relation='',
                     old_field=''):
        """
        Generate xml for an object recursively
        """
        irm = self.env['ir.model']
        if isinstance(relation, int):
            irms = irm.browse(relation)
        else:
            irms = irm.search([('model', '=', relation)], limit=1)

        if not irms:
            _logger.error('Model %s not found !' % relation)

        ##
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
        if isinstance(relation, int):
            relation = irms.model

        irm_name = self.format_element(irms.name)
        if old_field:
            x = Element(self.format_element(old_field), relation=relation,
                        id=str(object_id))
        else:
            x = Element(irm_name, id='%s' % object_id)

        if not object_id:
            return x

        if isinstance(object_id, (int, long)):
            object_id = [object_id]

        obj = self.env[relation]
        mod_ids = obj.browse(object_id).read()
        mod_fields = obj.fields_get()
        for mod in mod_ids:
            for f in mod_fields:
                field = f.lower()
                name = mod_fields[f]['string']
                type = mod_fields[f]['type']
                value = mod[f]
                e = Element(field, label='%s' % self.format_element(name))
                if type in ['char', 'text', 'selection', 'html']:
                    e.text = value and unicode(value) or ''
                elif type == 'integer':
                    e .text = value and str(value) or '0'
                elif type in ['float', 'monetary']:
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
                    # _logger.error('Current: %r Old: %r' % (mod_fields[f]['relation'], relation))
                    if depth > 0 and value and mod_fields[f]['relation'] != old_relation and mod_fields[f]['relation'] not in ban:
                        e = self.generate_xml(mod_fields[f]['relation'], value, depth - 1, relation, field)
                    else:
                        e.set('id', '%r' % value or 0)
                        if not isinstance(value, int):
                            e.text = str(mod[f][1])
                elif type in ['one2many', 'many2many']:
                    if depth > 0 and value and \
                       mod_fields[f]['relation'] not in ban:
                        for v in value:
                            x.append(self.generate_xml(mod_fields[f]['relation'], v,
                                                       depth - 1, relation, field))
                        continue
                    else:
                        e.set('id', '%r' % value)
                elif type in ['binary', 'reference']:
                    e.text = 'Not supported'
                else:
                    _logger.error('Type not supported: field-> %s, name-> %s, type->%s' % (field, name, type))
                x.append(e)
        return x

    @api.model
    def generatorYAML(self, jasper_document, current_object, user_company):

        import yaml
        root = Element('data')

        ctx = self.env.context.copy()
        for yaml_object in jasper_document.yaml_object_ids:

            model_obj = self.env[yaml_object.model.model].with_context(ctx)
            user_id = self.env.uid
            if yaml_object.user_id.id:
                user_id = yaml_object.user_id.id
            if yaml_object.context:
                yaml_context = literal_eval(yaml_object.context)

                for key, value in yaml_context.items():
                    ctx[key] = value
            aux = yaml_object.domain
            my_args = []
            if aux:
                aux = aux.replace('[[', '').replace(']]', '')
                my_args = eval(aux, {'o': current_object, 'c': user_company, 't': time, 'u': self.env.user}) or ''
            models = model_obj.sudo(user_id).search(args=my_args,
                                                    offset=yaml_object.offset,
                                                    limit=yaml_object.limit if yaml_object.limit > 0 else None,
                                                    order=yaml_object.order)

            xmlObject = Element('object')
            xmlObject.set("name", yaml_object.name)
            xmlObject.set("model", yaml_object.model.name)
            for object in models:
                xmlField = Element('container')

                # take the field name if it exists in model and if name is not False
                # else take the rec_name value if a rec_name was used
                # else take simply the object id

                if 'name' in object._fields and object.name:
                    xmlField.set("name", object.name)
                elif object._rec_name != None:
                    rec_name_value = object.read([object._rec_name])[object._rec_name]
                    if rec_name_value:
                        xmlField.set("name", rec_name_value)
                    else:
                        xmlField.set("name", str(object.id))
                else:
                    xmlField.set("name", str(object.id))
                self.sudo(user_id).with_context(ctx).generate_from_yaml(xmlField,
                                                                        object,
                                                                        yaml.load(yaml_object.fields))
                xmlObject.append(xmlField)

            root.append(xmlObject)

        return tostring(root, pretty_print=ctx.get('indent', False))

    @api.model
    def generate_from_yaml(self, root, object, fields, prefix=''):
        """
        Generate xml for an object recursively
        """

        if prefix:
            prefix = '%s_' % (prefix, )

        for field in fields:

            if type(field) is dict:
                fieldname = field.keys()[0]
                value = field.values()[0]
                xmlField = Element(prefix + fieldname)

                if object._fields[fieldname].type in ['one2many','many2many']:  # o2m, m2m
                    for objectListElement in object[fieldname]:
                        xmlContainerField = Element("container")
                        xmlContainerField.set("name", fieldname)
                        self.generate_from_yaml(xmlContainerField, objectListElement, value, prefix + fieldname)

                        xmlField.append(xmlContainerField)
                elif object._fields[fieldname].type == 'many2one':  # m2o
                    if object[fieldname]:
                        self.generate_from_yaml(xmlField, object[fieldname], value, prefix + fieldname)
                else:
                    # set element content
                    xmlField.text = self._format_element(xmlField, object._fields[field].type, object[fieldname])

            else:
                xmlField = Element(prefix + field)

                # set element content
                xmlField.text = ''
                if object:
                    xmlField.text = self._format_element(xmlField, object._fields[field].type, object[field])

            root.append(xmlField)
        return

    def _format_element(self, element, field_type, field_value):

        if field_type in ['char', 'text', 'selection', 'html']:
            return field_value and unicode(field_value) or ''
        elif field_type == 'integer':
            return field_value and str(field_value) or '0'
        elif field_type in ['float', 'monetary']:
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
            raise EvalError(_('Many2One'),
                            _('You cannot use many2one directly.\n\nDefine subelement for: "%s"') % (str(element.tag),)
                            )
        elif field_type in ['binary', 'reference']:
            if field_value:
                return str(field_value)
            else:
                return ''
        else:
            _logger.error('Type not supported: field_type-> %s, element-> %s, field_value->%s' % (field_type,
                                                                                                  element,
                                                                                                  field_value))

    def generator(self, model, res_id, depth):
        root = Element('data')
        root.append(self.generate_context())
        root.append(self.generate_xml(model, res_id, depth))
        return tostring(root, pretty_print=self.env.context.get('indent', False))
