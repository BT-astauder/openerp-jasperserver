# -*- coding: utf-8 -*-
##############################################################################
#
#    jasper_server module for OpenERP,
#    Copyright (C) 2010-2011 SYLEAM Info Services (<http://www.syleam.fr/>)
#                  Christophe CHAUVET <christophe.chauvet@syleam.fr>
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

import os
import time
import base64
import logging

from odoo.report.render import render
from odoo import _
# from httplib2 import Http, ServerNotFoundError, HttpLib2Error
from parser import WriteContent, ParseResponse
from .common import parameter_dict, merge_pdf
from report_exception import JasperException, EvalError
from pyPdf import PdfFileWriter, PdfFileReader
from odoo.addons.jasper_server.common import jasperlib as jslib
from odoo import netsvc
from odoo.exceptions import AccessError, UserError

from xml.etree import ElementTree as et
import sys
import traceback

_logger = logging.getLogger('odoo.addons.jasper_server.report')

##
# If cStringIO is available, we use it
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO  # noqa


class external_pdf(render):
    def __init__(self, pdf, doc_format='pdf'):
        render.__init__(self)
        self.content = pdf
        self.output_type = doc_format

    def _render(self):
        return self.content

    def set_output_type(self, format):
        """
        Change the format of the file

        :param format: file format (eg: pdf)
        :type  format: str
        """
        self.output_type = format

    def get_output_type(self,):
        """
        Retrieve the format of the attachment
        """
        return self.output_type


def log_debug(message):
    if _logger.isEnabledFor(logging.DEBUG):
        _logger.debug(' %s' % message)


class hashabledict(dict):
        def __hash__(self):
            return hash(tuple(sorted(self.items())))


class Report(object):
    """
    compose the SOAP Query, launch the query and return the value
    """
    def __init__(self, name, env, res_ids, data):
        """Initialise the report"""
        self.name = name
        self.service = name.replace('report.jasper.report_', '')
        self.ids = res_ids
        self.data = data
        self.attrs = data.get('form', {})
        self.custom = data.get('jasper', {})
        self.model = data.get('model', False)
        self.env = env
        self.outputFormat = 'PDF'
        self.path = None

        # Reuse object pool
        model_obj = None
        if self.model:
            model_obj = self.env[self.model]
        self.model_obj = model_obj
        self.obj = None

    def add_attachment(self, res_id, aname, content, mimetype='binary'):
        """
        Add attachment for this report
        """
        name = aname + '.' + self.outputFormat.lower()
        ctx = self.env.context.copy()
        ctx['type'] = mimetype
        ctx['default_type'] = 'binary'

        return self.env['ir.attachment'].with_context(ctx).create({'name': name,
                                                                   'datas': base64.encodestring(content),
                                                                   'datas_fname': name,
                                                                   'mimetype': mimetype,
                                                                   'res_model': self.model,
                                                                   'res_id': res_id
                                                                   })

    def _eval_field(self, cur_obj, fieldcontent):
        """
        Evaluate the field
        """
        try:
            return eval(fieldcontent, {'object': cur_obj, 'time': time})
        except SyntaxError, e:
            _logger.warning('Error %s' % str(e))
            raise EvalError(_('Field Eval Error'),
                            _('Syntax error when evaluate field\n\nMessage: "%s"') % str(e))  # noqa
        except NameError, e:
            _logger.warning('Error %s' % str(e))
            raise EvalError(_('Field Eval Error'),
                            _('Error when evaluate field\n\nMessage: "%s"') % str(e))  # noqa
        except AttributeError, e:
            _logger.warning('Error %s' % str(e))
            raise EvalError(
                _('Field Eval Error'),
                _('Attribute error when evaluate field\nVerify if specify field exists and valid\n\nMessage: "%s"'
                  ) % str(e))  # noqa
        except Exception, e:
            _logger.warning('Error %s' % str(e))
            raise EvalError(_('Field Eval Error'),
                            _('Unknown error when evaluate field\nMessage: "%s"') % str(e))  # noqa

    def _eval_attachment(self, cur_obj):
        """
        Launch eval on attachment field, and return the value
        """
        attachment = self.attrs['attachment']
        aux_object = attachment.find('object')
        aux_time = attachment.find('time')
        if aux_object >= 0 or aux_time >= 0:
            try:
                if aux_object >= 0:
                    aux_input = attachment[attachment.find('object'):]
                    aux_input = aux_input[0:aux_input.find('_')]
                    aux_object_eval = eval(aux_input, {'object': cur_obj})
                    attachment = attachment.replace(aux_input, aux_object_eval)
                if aux_time >= 0:
                    aux_input = attachment[attachment.find('time'):]
                    aux_input = aux_input[0:aux_input.find('_')]
                    aux_time_eval = eval(aux_input, {'time': time})
                    attachment = attachment.replace(aux_input, aux_time_eval)
            except SyntaxError, e:
                _logger.warning('Error %s' % str(e))
                raise EvalError(_('Attachment Error'),
                                _('Syntax error when evaluate attachment\n\nMessage: "%s"') % str(e))  # noqa
            except NameError, e:
                _logger.warning('Error %s' % str(e))
                raise EvalError(_('Attachment Error'),
                                _('Error when evaluate attachment\n\nMessage: "%s"') % str(e))  # noqa
            except AttributeError, e:
                _logger.warning('Error %s' % str(e))
                raise EvalError(
                    _('Attachment Error'),
                    _('Attribute error when evaluate attachment\nVerify if specify field exists and valid\n\nMessage: "%s"'
                      ) % str(e))  # noqa
            except Exception, e:
                _logger.warning('Error %s' % str(e))
                raise EvalError(_('Attachment Error'),
                                _('Unknown error when evaluate attachment\nMessage: "%s"') % str(e))  # noqa
        return attachment


    def _eval_duplicate(self, cur_obj, current_document):
        """
        Evaluate the duplicate field
        """
        try:
            return int(eval(current_document.duplicate, {'o': cur_obj}))
        except SyntaxError, e:
            _logger.warning('Error %s' % str(e))
            raise EvalError(_('Duplicate Error'),
                            _('Syntax error when evaluate duplicate\n\nMessage: "%s"') % str(e))  # noqa
        except NameError, e:
            _logger.warning('Error %s' % str(e))
            raise EvalError(_('Duplicate Error'),
                            _('Error when evaluate duplicate\n\nMessage: "%s"') % str(e))  # noqa
        except AttributeError, e:
            _logger.warning('Error %s' % str(e))
            raise EvalError(
                _('Duplicate Error'),
                _('Attribute error when evaluate duplicate\nVerify if specify field exists and valid\n\nMessage: "%s"'
                  ) % str(e))  # noqa
        except Exception, e:
            _logger.warning('Error %s' % str(e))
            raise EvalError(_('Duplicate Error'),
                            _('Unknown error when evaluate duplicate\nMessage: "%s"') % str(e))  # noqa

    def _eval_lang(self, cur_obj, current_document):
        """
        Evaluate the lang field
        """

        try:
            return eval(current_document.lang, {'o': cur_obj, 'ctx': self.env.context})
        except SyntaxError, e:
            _logger.warning('Error %s' % str(e))
            raise EvalError(_('Language Error'),
                            _('Syntax error when evaluate language\n\nMessage: "%s"') % str(e))  # noqa
        except NameError, e:
            _logger.warning('Error %s' % str(e))
            raise EvalError(_('Language Error'),
                            _('Error when evaluate language\n\nMessage: "%s"') % str(e))  # noqa
        except AttributeError, e:
            _logger.warning('Error %s' % str(e))
            raise EvalError(
                _('Language Error'),
                _('Attribute error when evaluate language\nVerify if specify field exists and valid\n\nMessage: "%s"'
                  ) % str(e))  # noqa
        except Exception, e:
            _logger.warning('Error %s' % str(e))
            raise EvalError(_('Language Error'),
                            _('Unknown error when evaluate language\nMessage: "%s"') % str(e))  # noqa

    def _jasper_execute(self, res_id, current_document, jasper_server, pdf_list):
        """
        After retrieve datas to launch report, execute it and
        return the content
        """
        # Issue 934068 with web client with model is missing from the context
        if not self.model:
            self.model = current_document.model_id.model
            self.model_obj = self.env[self.model]

        content = None

        cur_obj = self.model_obj.browse(res_id)
        aname = False
        if self.attrs['attachment']:
            aname = self._eval_attachment(cur_obj)

        duplicate = 1
        if current_document.duplicate:
            duplicate = self._eval_duplicate(cur_obj, current_document)

        log_debug('Number of duplicate copy: %d' % int(duplicate))

        # If language is set in the jasper document we get it, otherwise language is by default American English
        language = self.env.context.get('lang', 'en_US')
        if current_document.lang:
            language_aux = self._eval_lang(cur_obj, current_document)
            # type is str if language is given directly as string 'de_DE' for instance
            if isinstance(language_aux, list) and language_aux[0][0]:
                language = language_aux[0][0]

        # Check if we can launch this reports
        # Test can be simple, or in a function
        if current_document.check_sel != 'none':
            try:
                if current_document.check_sel == 'simple' and \
                   not eval(current_document.check_simple, {'o': cur_obj}):
                    raise JasperException(_('Check Print Error'), current_document.message_simple)  # noqa
                elif current_document.check_sel == 'func' and \
                        not hasattr(self.model_obj, 'check_print'):
                    raise JasperException(_('Check Print Error'),
                                          _('"check_print" function not found in "%s" object') % self.model)  # noqa
                elif current_document.check_sel == 'func' and \
                        hasattr(self.model_obj, 'check_print') and \
                        not cur_obj.check_print():
                    raise JasperException(_('Check Print Error'), _('Function "check_print" return an error'))  # noqa

            except SyntaxError, e:
                _logger.warning('Error %s' % str(e))
                raise EvalError(_('Check Error'),
                                _('Syntax error when check condition\n\nMessage: "%s"') % str(e))  # noqa
            except NameError, e:
                _logger.warning('Error %s' % str(e))
                raise EvalError(_('Check Error'),
                                _('Error when check condition\n\nMessage: "%s"') % str(e))  # noqa
            except AttributeError, e:
                _logger.warning('Error %s' % str(e))
                raise EvalError(
                    _('Check Error'),
                    _('Attribute error when check condition\nVerify if specify field exists and valid\n\nMessage: "%s"'
                      ) % str(e))  # noqa
            except JasperException, e:
                _logger.warning('Error %s' % str(e))
                raise JasperException(e.title, e.message)
            except Exception, e:
                _logger.warning('Error %s' % str(e))
                raise EvalError(_('Check Error'),
                                _('Unknown error when check condition\nMessage: "%s"') % str(e))  # noqa

        reload_ok = False
        if self.attrs['reload'] and aname:
            _logger.info('Printing must be reload from attachment if exists (%s)' % aname)  # noqa
            name_with_output_format = '%s.%s' % (aname, self.outputFormat.lower())
            aids = self.env['ir.attachment'].search([('name', '=', name_with_output_format),
                                                     ('res_model', '=', self.model),
                                                     ('res_id', '=', res_id)],
                                                    order='id desc',
                                                    limit=1)
            if aids:
                reload_ok = True
                _logger.info('Attachment found, reloading it!')
                if aids.datas:
                    d = base64.decodestring(aids.datas)
                    WriteContent(d, pdf_list)
                    content = d
            else:
                _logger.info('Attachment not found: looked for name={0}, '
                             'res_model={1}, res_id={2} in ir.attachment'.format(aname, self.model, res_id))

        if not reload_ok:
            # Bug found in iReport >= 3.7.x (IN doesn't work in SQL Query)
            # We cannot use $X{IN, field, Collection}
            # use $P!{OERP_ACTIVE_IDS} indeed as
            # ids in ($P!{OERP_ACTIVE_IDS} (exclamation mark)
            d_par = {
                'active_id': res_id,
                'active_ids': ','.join(str(i) for i in [res_id]),
                'model': self.model,
                'sql_query': self.attrs.get('query', "SELECT 'NO QUERY' as nothing"),  # noqa
                'sql_query_where': self.attrs.get('query_where', '1 = 1'),
                'report_name': self.attrs.get('report_name', _('No report name')),  # noqa
                'lang': language or 'en_US',
                'duplicate': duplicate,
                'dbname': self.env.cr.dbname,
                'uid': self.env.uid,
            }

            # If XML we must compose it
            if self.attrs['params'][2] == 'xml':
                d_xml = self.env['jasper.server'].generator(self.model,
                                                            self.ids[0],
                                                            self.attrs['params'][3])
                d_par['xml_data'] = d_xml

            # Retrieve the company information and send them in parameter
            # Is document have company field, to print correctly the document
            # Or take it to the user
            if hasattr(cur_obj, 'company_id') and cur_obj.company_id:
                cny = cur_obj.company_id
            else:
                cny = self.env.user.company_id

            d_par.update({
                'company_name': cny.name,
                'company_logo': cny.name.encode('ascii',
                                                'ignore').replace(' ', '_'),
                'company_header1': cny.rml_header1 or '',
                'company_footer1': cny.rml_footer or '',
                'company_footer2': '',
                'company_website': cny.partner_id.website or '',
                'company_currency': cny.currency_id.name or '',

                # Search the default address for the company.
                'company_street': cny.partner_id.street or '',
                'company_street2': cny.partner_id.street2 or '',
                'company_zip': cny.partner_id.zip or '',
                'company_city': cny.partner_id.city or '',
                'company_country': cny.partner_id.country_id.name or '',
                'company_phone': cny.partner_id.phone or '',
                'company_fax': cny.partner_id.fax or '',
                'company_mail': cny.partner_id.email or '',
            })

            # Parameters are evaluated
            for p in current_document.param_ids:
                if p.code and p.code.startswith('[['):
                    d_par[p.name.lower()] = eval(p.code.replace('[[', '').replace(']]', ''),
                                                 {'o': cur_obj,
                                                  'c': cny,
                                                  't': time,
                                                  'u': self.env.user}) or ''  # noqa
                else:
                    d_par[p.name] = p.code

            # If date_format is not given as parameter, it's set from the language
            if not 'date_format' in d_par:
                my_language = self.env['res.lang'].search([("code", "=", language)], limit=1)
                if my_language:
                    date_format = my_language.date_format
                    # Date format is changed because JasperSoft does not accept format based on %.
                    # It needs usual format for dates
                    date_format = date_format.replace("%d",'dd')
                    date_format = date_format.replace("%m",'MM')
                    date_format = date_format.replace("%Y",'YYYY')
                    d_par['date_format'] = date_format

            # If YAML we must compose it
            if self.attrs['params'][2] == 'yaml':
                #Using language coming from the jasper document if exists
                my_context = self.env.context.copy()
                my_context['lang'] = language
                d_xml = self.env['jasper.server'].with_context(my_context).generatorYAML(current_document,
                                                                                         cur_obj,
                                                                                         cny)

                if current_document.debug:
                    return d_xml, 1
                d_par['xml_data'] = d_xml

            # If RML, call original report
            if self.attrs['params'][2] == 'rml':
                serviceName = 'report.rml2jasper.' + self.name[7:]  # replace "report."
                srv = netsvc.Service._services[serviceName]

                mycontext = self.env.context.copy()
                data = self.data.copy()
                data['report_type'] = 'raw'
                mycontext['called_from_jasper'] = True
                (result, format) = srv.with_context(mycontext).create(self.ids, data)
                if current_document.debug:
                    return result, 1
                d_par['xml_data'] = result

            self.outputFormat = current_document.jasper_document_extension_id.extension.lower()
            special_dict = {
                'TIME_ZONE': 'UTC',
                'REPORT_DATE_FORMAT': "dd_MM_yyyy",
                'XML_DATE_PATTERN': 'yyyy-MM-dd HH:mm:ss',
                'REPORT_LOCALE': language or 'en_US',
                'IS_JASPERSERVER': 'yes',
            }

            # we must retrieve label in the language document
            # (not user's language)
            for l in current_document.with_context({'lang': language}).label_ids:
                special_dict['I18N_' + l.name.upper()] = l.value or ''

            # If report is launched since a wizard,
            # we can retrieve some parameters
            for d in self.custom.keys():
                special_dict['CUSTOM_' + d.upper()] = self.custom[d]

            # If special value is available in context,
            # we add them as parameters
            if self.env.context.get('jasper') and isinstance(self.env.context['jasper'], dict):
                for d in self.env.context['jasper'].keys():
                    special_dict['CONTEXT_' + d.upper()] = self.env.context['jasper'][d]

            par = parameter_dict(self.attrs, d_par, special_dict)

            # add generated XML to the service input params
            if 'xml_data' in d_par:
                par['XML_DATA'] = d_par['xml_data']

            # ##
            # # Execute the before query if it available
            # #
            # The following lines have been commented because jasper_server does not define before,
            # The model which defines it is jasper.document
            # if jasper_server.get('before'):
            #     self.cr.execute(jasper_server['before'], {'id': res_id})

            try:
                js = jslib.Jasper(jasper_server.host, jasper_server.port, jasper_server.user, jasper_server.password)
                js.auth(language)
                envelop = js.run_report(uri=self.path or self.attrs['params'][1], output=self.outputFormat, params=par)
                response = js.send(jslib.SoapEnv('runReport', envelop).output())
                content = response['data']
                mimetype = response['content-type']
                ParseResponse(response, pdf_list, self.outputFormat.lower())
            except jslib.ServerNotFound:
                raise JasperException(_('Error'), _('Server not found !'))
            except jslib.AuthError:
                raise JasperException(_('Error'), _('Authentication failed !'))
            except Exception as e:
                raise JasperException(_('Error'), e)

            # Store the content in ir.attachment if ask
            if aname:
                self.add_attachment(res_id, aname, content, mimetype=mimetype)

            # Execute the before query if it available
            # The following lines have been commented because jasper_server does not define after,
            # The model which defines it is jasper.document
            # if jasper_server.get('after'):
            #     self.env.cr.execute(jasper_server['after'], {'id': res_id})

            # Update the number of print on object
            fld = self.model_obj.fields_get()
            if 'number_of_print' in fld:
                cur_obj.number_of_print = (getattr(cur_obj, 'number_of_print', None) or 0) + 1

        return content, duplicate

    # Function to merge two XML
    # http://stackoverflow.com/questions/14878706/merge-xml-files-with-nested-elements-without-external-libraries
    def combine_element(self, one, other):
        """
        This function recursively updates either the text or the children
        of an element if another element is found in `one`, or adds it
        from `other` if not found.
        """
        # Create a mapping from tag name to element, as that's what we are fltering with
        mapping = {(el.tag, hashabledict(el.attrib)): el for el in one}
        for el in other:
            if len(el) == 0:
                # Not nested
                try:
                    # Update the text
                    mapping[(el.tag, hashabledict(el.attrib))].text = el.text
                except KeyError:
                    # An element with this name is not in the mapping
                    mapping[(el.tag, hashabledict(el.attrib))] = el
                    # Add it
                    one.append(el)
            else:
                try:
                    # Recursively process the element, and update it in the same way
                    self.combine_element(mapping[(el.tag, hashabledict(el.attrib))], el)
                except KeyError:
                    # Not in the mapping
                    mapping[(el.tag, hashabledict(el.attrib))] = el
                    # Just add it
                    one.append(el)

    def execute(self):
        """Launch the report and return it"""
        context = self.env.context.copy()
        # The following line is required in v10 to get discount lines in the Reports
        context['custom_search_line_discount'] = True
        self.env = self.env(context=context)

        ids = self.ids
        log_debug('DATA:')
        log_debug('\n'.join(['%s: %s' % (x, self.data[x]) for x in self.data]))

        ##
        # For each IDS, launch a query, and return only one result
        #
        pdf_list = []
        doc = False
        if self.service:
            try:
                service_id = int(self.service)
                doc = self.env['jasper.document'].search([('id', '=', service_id)], limit=1)
            except ValueError:
                report_name = self.service
                report_str = self.service[0:7]
                if report_str == "report.":
                    report_name = self.service[7:]  # remove "report."
                    doc = self.env['jasper.document'].search([('rml_ir_actions_report_xml_name', '=', report_name)],
                                                             limit=1)
                else:
                    doc = self.env['jasper.document'].search(
                        [('report_id.report_name', '=', 'jasper.report_%s' % (report_name,))],
                        limit=1)

        if not doc:
            raise JasperException(_('Configuration Error'),
                                  _("Service name doesn't match!"))

        self.outputFormat = doc.jasper_document_extension_id.extension
        if doc.debug:
            self.outputFormat = 'XML'
        log_debug('Format: %s' % doc.jasper_document_extension_id.extension)

        if doc.server_id:
            js = doc.server_id
        else:
            js = self.env['jasper.server'].search([('enable', '=', True)], limit=1)
            if not len(js):
                doc.add_error_message(_('Configuration Error:'),
                                      _('No JasperServer configuration found!'))
                raise JasperException(_('Configuration Error'),
                                      _('No JasperServer configuration found!'))  # noqa

        def compose_path(basename):
            return js.prefix and '/' + js.prefix + '/instances/%s/%s' or basename   # noqa

        self.attrs['attachment'] = doc.attachment
        self.attrs['reload'] = doc.attachment_use
        if not self.attrs.get('params'):
            if doc.any_database:
                uri = compose_path('/odoo/bases/%s') % (doc.report_unit)
            else:
                uri = compose_path('/odoo/bases/%s/%s') % (self.env.cr.dbname, doc.report_unit)
            self.attrs['params'] = (doc.jasper_document_extension_id.extension, uri, doc.mode, doc.depth, {})

        all_xml = []
        one_check = {
            doc.id: False
        }
        content = ''
        duplicate = 1

        # in RML we maybe have no records, but data
        if not doc.mode == 'rml':
            for current_id in ids:
                if doc.mode == 'multi' and self.outputFormat.upper() == 'PDF':
                    for d in doc.child_ids:
                        if d.only_one and one_check.get(d.id, False):
                            continue
                        if doc.any_database:
                            self.path = compose_path('/odoo/bases/%s') % (d.report_unit,)
                        else:
                            self.path = compose_path('/odoo/bases/%s/%s') % (self.env.cr.dbname, d.report_unit)
                        (content, duplicate) = self._jasper_execute(current_id, d, js, pdf_list)
                        one_check[d.id] = True
                else:
                    if doc.only_one and one_check.get(doc.id, False):
                        continue
                    error_message_interface = False
                    try:
                        error_title = ''
                        error_message = ''
                        (content, duplicate) = self._jasper_execute(current_id, doc, js, pdf_list)
                        all_xml.append(content)
                    except KeyError as e:
                        error_title = 'KeyError'
                        error_message = e.message
                    except IndentationError as e:
                        error_title = 'IndentationError'
                        error_message = e.message
                    except AccessError as e:
                        doc.add_error_message('AccessError', e.name)
                        raise AccessError(e.name)
                    except EvalError as e:
                        error_title = 'EvalError: %s' % (e.name,)
                        error_message = e.message
                    except ValueError as e:
                        error_title = 'ValueError'
                        error_message = e.message
                    except TypeError as e:
                        error_title = 'TypeError'
                        error_message = e.message
                    except JasperException as e:
                        error_title = 'JasperException'
                        error_message = e.message
                    except Exception as e:

                        type_, value_, traceback_ = sys.exc_info()
                        exception = traceback.format_exception(type_, value_, traceback_)

                        # self.add_error_message(doc,e[0],e[1])
                        if isinstance(e, list):
                            ex_all = e[0] + ' : ' + e[1] + '\n'
                            for item in exception:
                                ex_all = ex_all + item
                            doc.add_error_message(e[0], ex_all)
                            raise Exception(e.name, e.value)
                        elif isinstance(e, unicode):
                            error_title = e
                            error_message = ''
                        else:
                            if hasattr(e, 'value'):
                                if isinstance(e.value, unicode):
                                    error_title = e.name
                                    error_message = e.value
                                elif isinstance(e.value, UnicodeEncodeError):
                                    error_title = e.name
                                    error_message = '%s - probably due to: %s' % (unicode(e.value), e.value.object)
                                    error_message_interface = '%s\n\nIt probably comes from:\n' \
                                                              '- %s\n' % (unicode(e.value), e.value.object)
                            else:
                                error_message = 'Unknown'
                                if hasattr(e, 'value'):
                                    error_message = e.value
                                    if hasattr(e.value, 'message'):
                                        error_message = e.value.message
                                elif hasattr(e, 'message'):
                                    error_message = e.message
                                    if hasattr(e.message, 'message'):
                                        error_message = e.message.message
                                error_title = str(type(e))
                                if hasattr(e, 'name'):
                                    error_title = e.name
                                elif hasattr(e, 'title'):
                                    error_title = e.title
                    if error_title or error_message:
                        doc.add_error_message(error_title, error_message)
                        if not error_message_interface:
                            raise UserError('%s: %s' % (error_title, error_message))
                        else:
                            raise UserError('%s: %s' % (error_title, error_message_interface))
        else:
            for current_id in ids:
                if doc.mode == 'multi' and self.outputFormat.upper() == 'PDF':
                    for d in doc.child_ids:
                        if d.only_one and one_check.get(d.id, False):
                            continue
                        if doc.any_database:
                            self.path = compose_path('/odoo/bases/%s') % (d.report_unit,)
                        else:
                            self.path = compose_path('/odoo/bases/%s/%s') % (self.env.cr.dbname, d.report_unit)
                        (content, duplicate) = self._jasper_execute(current_id, d, js, pdf_list)
                        one_check[d.id] = True
                else:
                    if not (doc.only_one and one_check.get(doc.id, False)):
                        (content, duplicate) = self._jasper_execute(current_id, doc, js, pdf_list)
                        one_check[doc.id] = True

        # If format is not PDF, we return it directly
        # ONLY PDF CAN BE MERGE!
        if self.outputFormat.upper() != 'PDF':
            self.obj = external_pdf(content, self.outputFormat)

            # #
            # # We use function combine_elements to merge all XML in unique file
            # #
            if self.outputFormat.upper() == 'XML':
                # To merge XML, result_xml wil contain the XML merged till now.
                # For first instance, it just contains general structure
                result_xml = "<data></data>"
                for item in all_xml:
                    one = et.fromstring(result_xml)
                    other = et.fromstring(item)
                    # Merging two XML strings that were converted to XML Elements
                    self.combine_element(one, other)

                    # Updating content of self.obj, that is in the end what we return
                    self.obj.content =  et.tostring(one)
                    # Update resulting XML string for next iteration
                    result_xml = self.obj.content
            elif self.outputFormat.upper() == 'CSV':
                # For first item we leave the header but for the next items we remove the header
                content = ''
                for x in all_xml:
                    if content == '':
                        content = content + x
                    else:
                        content = content + x.split('\n')[1] + '\n'
                self.obj.content = content

            return self.obj.content, self.outputFormat

        def find_pdf_attachment(pdfname, current_obj):
            """
            Evaluate the pdfname, and return it as a field object
            """
            if not pdfname:
                return None

            filename = self._eval_field(current_obj, pdfname)
            att = self.env['ir.attachment'].search([('name', '=', filename),
                                                    ('res_model', '=', self.model_obj._name),
                                                    ('res_id', '=', current_id)],
                                                   limit=1)
            ret = None
            if att and att.datas:
                datas = StringIO()
                datas.write(base64.decodestring(att.datas))
                ret = datas.getvalue()
            return ret

        # If We must add begin and end file in the current PDF
#        cur_obj = self.model_obj.browse(self.cr, self.uid, ex, context=context)
#        pdf_fo_begin = find_pdf_attachment(doc.pdf_begin, cur_obj)
#        pdf_fo_ended = find_pdf_attachment(doc.pdf_ended, cur_obj)

        # We use pyPdf to merge all PDF in unique file
        c = StringIO()
        if len(pdf_list) > 1 or duplicate > 1:
            # content = ''
            tmp_content = PdfFileWriter()

            # We add all PDF file in a list of file pointer to close them
            # at the end of treatment
            tmp_pdf_list = []
            for curpdf in pdf_list:
                tmp_pdf_list.append(open(curpdf, 'r'))

            for fo_pdf in tmp_pdf_list:
                for x in range(0, duplicate):
                    fo_pdf.seek(0)
                    tmp_pdf = PdfFileReader(fo_pdf)
                    for page in range(tmp_pdf.getNumPages()):
                        tmp_content.addPage(tmp_pdf.getPage(page))
            else:
                tmp_content.write(c)
                # content = c.getvalue()

            # It seem there is a bug on PyPDF if we close the "fp" file,
            # we cannot call tmp_content.write(c) We received
            # an exception "ValueError: I/O operation on closed file"
            for fo_pdf in tmp_pdf_list:
                if not fo_pdf.closed:
                    fo_pdf.close()

        elif len(pdf_list) == 1:
            fp = open(pdf_list[0], 'r')
            c.write(fp.read())
            fp.close()

        # Remove all files on the disk
        for f in pdf_list:
            os.remove(f)

        # If covers, we merge PDF
        # fo_merge = merge_pdf([pdf_fo_begin, c, pdf_fo_ended])
        # fo_merge = merge_pdf([c])
        # fo_merge.getvalue()
        # fo_merge.close()

        content = c.getvalue()

        if not c.closed:
            c.close()

        self.obj = external_pdf(content, self.outputFormat)
        return self.obj.content, self.outputFormat
