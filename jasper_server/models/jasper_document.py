# -*- coding: utf-8 -*-
##############################################################################
#
#    jasper_server module for OpenERP,
#    Copyright (C) 2010-2011 SYLEAM Info Services (<http://www.Syleam.fr/>)
#                            Damien CRIER
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
from odoo.exceptions import AccessError, MissingError, UserError, Warning
from odoo.tools.sql import drop_view_if_exists
from odoo import _
from StringIO import StringIO
from lxml import etree
import base64
from odoo.addons.jasper_server.common import jasperlib
from logging import getLogger
from time import strftime

_logger = getLogger(__name__)

JRXML_NS = {
    'root': 'http://jasperreports.sourceforge.net/jasperreports',
}


class JasperDocument(models.Model):
    _name = 'jasper.document'
    _description = 'Jasper Document'
    _order = 'sequence'

    def _default_jasper_document_extension_id(self):
        return self.env.ref('jasper_server.jasper_document_extension_2')

    name = fields.Char('Name', size=128, translate=True, required=True)
    enabled = fields.Boolean('Active', help="Indicates if this document is active or not")
    model_id = fields.Many2one('ir.model', 'Object Model', required=True)
    server_id = fields.Many2one('jasper.server', 'Server', help='Select specific JasperServer')
    group_ids = fields.Many2many('res.groups', 'jasper_wizard_group_rel',
                                 'document_id', 'group_id', 'Groups')
    depth = fields.Integer('Depth', required=True, default=0)
    format_choice = fields.Selection([('mono', 'Single Format'),
                                      ('multi', 'Multi Format')],
                                     'Format Choice', required=True,
                                     default='mono')
    jasper_document_extension_id = fields.Many2one('jasper.document.extension', 'Format',
                                                   default=_default_jasper_document_extension_id)
    report_unit = fields.Char('Report Unit', size=128, help='Enter the name for report unit in Jasper Server')
    mode = fields.Selection([('sql', 'SQL'),
                             ('xml', 'XML'),
                             ('multi', 'Multiple Report'),
                             ('yaml', 'YAML'),
                             ('rml', 'RML')],
                            'Mode', required=True,
                            default='sql')
    # The following fields are commented by Alvaro:
    # Code injection, may be source of unexpected behaviors
    # before = fields.Text('Before',
    #                      help='This field must be filled with a valid SQL request '
    #                           'and will be executed BEFORE the report edition')
    # after = fields.Text('After',
    #                     help='This field must be filled with a valid SQL request '
    #                          'and will be executed AFTER the report edition')
    attachment = fields.Char('Save As Attachment Prefix', size=255,
                             help='This is the filename of the attachment used to store the printing result. '
                                  'Keep empty to not save the printed reports. '
                                  'You can use a python expression with the object and time variables. '
                                  'Please, use "_" as the delimiter after the object and/or time fields. '
                                  'For example: "file_object.name_custom-time.ctime()_ext". '
                                  'Note: Do not include the file extension.',
                             default=False)
    attachment_use = fields.Boolean('Reload from Attachment',
                                    help='If you check this, then the second time the user prints with '
                                         'same attachment name, it returns the previous report.')
    param_ids = fields.One2many('jasper.document.parameter', 'document_id', 'Parameters')
    ctx = fields.Char('Context', size=128,
                      help="Enter condition with context does match to see the print action\n"
                           "eg: context.get('foo') == 'bar'")
    sql_view = fields.Text('SQL View', help='Insert your SQL view, if the report is base on it')
    sql_name = fields.Char('Name of view', size=128)
    child_ids = fields.Many2many('jasper.document', 'jasper_document_multi_rel',
                                 'source_id', 'destin_id',
                                 'Child report', help='Select reports to launch when this report is called')
    sequence = fields.Integer('Sequence', default=100,
                              help='The sequence is used when launch a multple report, to select the order to launch')
    only_one = fields.Boolean('Launch one time for all ids',
                              help='Launch the report only one time on multiple id')
    duplicate = fields.Char('Duplicate', size=256, default="'1'",
                            help="Indicate the number of duplicate copies, use 'o' as object to evaluate\n"
                                 "eg: o.partner_id.copy\nor\n'1'")
    lang = fields.Char('Lang', size=256, default=False,
                       help="Indicate the lang to use for this report, use o as object to evaluate\n"
                            "eg: o.partner_id.lang\nctx as context\neg: ctx.get(\'test'\)\nor\n'en_US'\n"
                            "default use user's lang")
    report_id = fields.Many2one('ir.actions.report.xml', 'Report', readonly=True, default=False,
                                help='Link to the report in ir.actions.report.xml')
    check_sel = fields.Selection([('none', 'None'),
                                  ('simple', 'Simple'),
                                  ('func', 'Function')],
                                 'Checking type', default='none',
                                 help='if None, no check\nif Simple, define on Check Simple the condition\n'
                                      'if function, the object have check_print function')
    check_simple = fields.Char('Check Simple', size=256, default=False,
                               help="This code inside this field must return True to send report execution\n"
                                    "eg o.state in ('draft', 'open')")
    message_simple = fields.Char('Return message', size=256, translate=True, default=False,
                                 help="Error message when check simple doesn't valid")
    label_ids = fields.One2many('jasper.document.label', 'document_id', 'Labels')
    # The following fields are commented by Alvaro:
    #  - They were not being used, so could be a source of confusion
    # pdf_begin = fields.Char('PDF at begin', size=128,
    #                         help='Name of the PDF file store as attachment to add at the first page '
    #                              '(page number not recompute)')
    # pdf_ended = fields.Char('PDF at end', size=128,
    #                         help='Name of the PDF file store as attachment to add at the last page '
    #                              '(page number not recompute)')

    # yaml fields
    yaml_object_ids = fields.One2many('jasper.yaml_object', 'jasper_document_id', string='YAML Object')
    debug = fields.Boolean('Debug')
    any_database = fields.Boolean('Available for any database')

    # RML fields
    rml_ir_actions_report_xml_id = fields.Many2one('ir.actions.report.xml', string='Report to generate RML')
    rml_ir_actions_report_xml_name = fields.Char(related='rml_ir_actions_report_xml_id.report_name',
                                                 string='Report to generate RML')
    error_text = fields.Text('Errors', readonly=True)

    @api.multi
    def make_action(self):
        """
        Create an entry in ir_actions_report_xml
        and ir.values
        """
        self.ensure_one()

        # Ignoring lang for creating the report name
        name_no_lang = self.with_context({}).name
        report_name = 'jasper.report_%s' % (name_no_lang.lower().replace(' ', '_'),)
        vals = {
            'name': self.name,
            'report_name': report_name,
            'model': self.model_id.model,
            'groups_id': [(6, 0, [x.id for x in self.group_ids])],
            'header': False,
            'multi': False,
        }
        report = self.report_id
        if report:
            _logger.info('Update "%s" service' % self.name)
            report.write(vals)
            # Loading translations
            langs = self.env['res.lang'].search_read(domain=[('code', '!=', 'en_US')], fields=['code'])
            for lang in langs:
                report.with_context(lang=lang['code']).name = self.with_context(lang=lang['code']).name
        else:
            _logger.info('Create "%s" service' % self.name)
            _logger.warning('    Update this module again in order to load the translation of "%s"' % self.name)
            vals.update({
                'report_type': 'jasper',
            })
            report = self.env['ir.actions.report.xml'].create(vals)
            # self.report_id = report
            # Using a query to avoid infinite recursion
            self._cr.execute("""UPDATE jasper_document SET report_id=%s
                                 WHERE id=%s""", (report.id, self.id))
            value = 'ir.actions.report.xml,' + str(report.id)
            self.env['ir.values'].set_action(name=self.name, action_slot='client_print_multi',
                                             model=self.model_id.model, action=value)

    @api.multi
    def action_values(self):
        """
        Search ids for reports
        """
        args = [
            ('key', '=', 'action'),
            ('key2', '=', 'client_print_multi'),
            ('value', '=', 'ir.actions.report.xml,%d' % self.report_id.id),
            # ('object', '=', True),
        ]
        return self.env['ir.values'].search(args)

    @api.model
    def get_action_report(self, module, name, datas=None):
        """
        Give the XML ID dans retrieve the report action

        :param module: name fo the module where the XMLID is reference
        :type module: str
        :param name: name of the XMLID (after the dot)
        :type name: str
        :param datas: data of the report
        :type name: dict
        :return: return an ir.actions.report.xml
        :rtype: dict
        """

        if datas is None:
            datas = {}

        report = self.env.ref('%s.%s' % (module, name))
        _logger.debug('get_action_report -> ' + report.report_name)

        return {
            'type': 'ir.actions.report.xml',
            'report_name': report.report_name,
            'datas': datas,
            'context': self._context,
        }

    @api.multi
    def create_values(self):
        self.ensure_one()
        if not self.action_values():
            value = 'ir.actions.report.xml,%d' % self.report_id.id
            _logger.debug('create_values -> ' + value)
            self.env['ir.values'].set_action(name=self.name, action_slot='client_print_multi',
                                             model=self.model_id.model, action=value)
        return True

    @api.multi
    def unlink_values(self):
        """
        Only remove link in ir.values, not the report
        """
        self.ensure_one()
        self.pool.get('ir.values').unlink(self.action_values())
        _logger.debug('unlink_values')
        return True

    @api.model
    def create(self, vals):
        """
        Dynamically declaring the wizard for this document
        """

        doc = super(JasperDocument, self).create(vals)
        doc.make_action()

        # Check if view and create it in the database
        if vals.get('sql_name') and vals.get('sql_view'):
            drop_view_if_exists(self._cr, vals.get('sql_name'))
            sql_query = 'CREATE OR REPLACE VIEW %s AS\n%s' % (vals['sql_name'],
                                                              vals['sql_view'])
            self._cr.execute(sql_query)
        return doc

    @api.multi
    def write(self, vals):
        """
        If the description change, we must update the action
        """

        cr = self._cr
        sql_view_or_name = False
        if vals.get('sql_name') or vals.get('sql_view'):
            sql_view_or_name = True
        action = False
        if not self._context.get('action'):
            action = True

        for jasper_document in self:
            if sql_view_or_name:
                sql_name = vals.get('sql_name', jasper_document.sql_name)
                sql_view = vals.get('sql_view', jasper_document.sql_view)
                drop_view_if_exists(cr, sql_name)
                sql_query = 'CREATE OR REPLACE VIEW %s AS\n%s' % (sql_name, sql_view)
                cr.execute(sql_query)
            if action:
                jasper_document.make_action()
                if 'enabled' in vals:
                    if vals['enabled']:
                        jasper_document.create_values()
                    else:
                        jasper_document.unlink_values()

        res = super(JasperDocument, self).write(vals)

        return res

    @api.multi
    def copy(self, default=None):
        """
        When we duplicate code, we must remove some field, before
        """
        self.ensure_one()

        if default is None:
            default = {}

        default['report_id'] = False
        default['name'] = self.name + _(' (copy)')

        new_yaml_object_ids = []
        for yaml_object in self.yaml_object_ids:
            new_yaml_object_ids.append((4, yaml_object.copy(default=None).id))
        new_param_ids = []
        for param in self.param_ids:
            new_param_ids.append((4, param.copy(default=None).id))
        new_label_ids = []
        for label in self.label_ids:
            new_label_ids.append((4, label.copy(default=None).id))

        default['yaml_object_ids'] = new_yaml_object_ids
        default['param_ids'] = new_param_ids
        default['label_ids'] = new_label_ids

        return super(JasperDocument, self).copy(default)

    @api.multi
    def unlink(self):
        """
        When remove jasper_document, we must remove data to
        ir.actions.report.xml and ir.values
        """

        for doc in self:
            if doc.report_id:
                doc.unlink_values()
                doc.report_id.unlink()

        return super(JasperDocument, self).unlink()

    @api.multi
    def check_report(self):
        self.ensure_one()
        js_server = self.env['jasper.server']
        if self.server_id:
            jss = self.server_id
        else:
            jss = js_server.search([('enable', '=', True)], limit=1)
            if not jss:
                raise MissingError(_('No JasperServer configuration found !'))

        def compose_path(basename):
            return jss['prefix'] and \
                '/' + jss['prefix'] + '/instances/%s/%s' or basename

        try:
            js = jasperlib.Jasper(jss.host, jss.port, jss.user, jss.password)
            js.auth()
            if self.any_database:
                uri = compose_path('/odoo/bases/%s') % (self.report_unit,)
            else:
                uri = compose_path('/odoo/bases/%s/%s') % (self._cr.dbname, self.report_unit)
            envelop = js.run_report(uri=uri, output='PDF', params={})
            response = js.send(jasperlib.SoapEnv('runReport', envelop).output())
            content = response['data']
            mimetype = response['content-type']
        except jasperlib.ServerNotFound:
            raise MissingError(_('Error, server not found %s %s') % (js.host, js.port))
        except jasperlib.AuthError:
            raise AccessError(_('Error, Authentication failed for %s/%s') % (js.user, js.pwd))
        except jasperlib.ServerError as e:
            raise UserError(str(e).decode('utf-8'))

        if content and mimetype:
            raise Warning(_("The check has been successful!"))
        else:
            raise UserError(_("Unknown error"))

        return True

    @api.multi
    def parse_jrxml(self, content, save_as_attachment):
        """
        Parse JRXML file to retrieve I18N parameters and OERP parameters
        """
        self.ensure_one()
        jasper_document_label = self.env['jasper.document.label']
        jasper_document_parameter = self.env['jasper.document.parameter']
        ir_attachment = self.env['ir.attachment']
        known_parameters = [
            'OERP_ACTIVE_ID', 'OERP_ACTIVE_IDS',
            'OERP_COMPANY_NAME', 'OERP_COMPANY_LOGO', 'OERP_COMPANY_HEADER1',
            'OERP_COMPANY_FOOTER1', 'OERP_COMPANY_FOOTER2', 'OERP_COMPANY_WEBSITE',
            'OERP_COMPANY_CURRENCY', 'OERP_COMPANY_STREET', 'OERP_COMPANY_STREET2',
            'OERP_COMPANY_ZIP', 'OERP_COMPANY_CITY', 'OERP_COMPANY_COUNTRY',
            'OERP_COMPANY_PHONE', 'OERP_COMPANY_FAX', 'OERP_COMPANY_MAIL',
        ]

        fp = StringIO(content)
        tree = etree.parse(fp)
        param = tree.xpath('//root:parameter/@name', namespaces=JRXML_NS)
        for label in param:
            val = tree.xpath('//root:parameter[@name="' + label + '"]//root:defaultValueExpression',
                             namespaces=JRXML_NS)
            if val:
                val = val[0].text
            else:
                val = ''

            _logger.debug('%s -> %s' % (label, val))

            if label.startswith('I18N_'):
                lab = label.replace('I18N_', '')
                label_ids = jasper_document_label.search([('name', '=', lab)])
                if label_ids:
                    continue
                jasper_document_label.create({
                    'document_id': self.id,
                    'name': lab,
                    'value': val.replace('"', ''),
                })
            if label.startswith('OERP_') and label not in known_parameters:
                lab = label.replace('OERP_', '')
                param_ids = jasper_document_parameter.search([('name', '=', lab)])
                if param_ids:
                    continue
                jasper_document_parameter.create({
                    'document_id': self.id,
                    'name': lab,
                    'code': val.replace('"', ''),
                    'enabled': True,
                })

        # We retrieve the name of the report with the attribute name from the jasperReport element
        filename = '%s.jrxml' % tree.xpath('//root:jasperReport/@name',
                                           namespaces=JRXML_NS)[0]

        attachments = ir_attachment.search([('name', '=', filename),
                                            ('res_model', '=', 'jasper.document'),
                                            ('res_id', '=', self.id)])
        if attachments:
            attachments.unlink()

        # Now we save JRXML as attachment if required
        if save_as_attachment:
            ctx = self._context.copy()
            ctx['type'] = 'binary'
            ctx['default_type'] = 'binary'
            ir_attachment.with_context(ctx).create({
                'name': filename,
                'datas': base64.encodestring(content),
                'datas_fname': filename,
                'file_type': 'text/xml',
                'res_model': 'jasper.document',
                'res_id': self.id
            })

        fp.close()
        return True

    @api.multi
    def add_error_message(self, error_title, error_message):
        self.ensure_one()
        new_error_txt = ''
        old_error_txt = self.error_text
        if old_error_txt:
            new_error_txt = old_error_txt
        new_error_txt = "{0}\n{1} {2} => {3} {4}".format(new_error_txt, strftime("%d/%m/%Y %H:%M:%S"),
                                                         self.env.user.name,
                                                         error_title, error_message)
        self.sudo().error_text = new_error_txt
        return True

    @api.multi
    def clean_error_messages(self):
        self.ensure_one()
        self.error_text = None
        return True
