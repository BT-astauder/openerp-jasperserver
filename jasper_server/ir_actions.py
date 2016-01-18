# -*- coding: utf-8 -*-
##############################################################################
#
#   jasper_server module for OpenERP, Management module for Jasper Server
#   Copyright (C) 2011 SYLEAM (<http://www.syleam.fr/>)
#             Christophe CHAUVET <christophe.chauvet@syleam.fr>
#
#   This file is a part of jasper_server
#
#   jasper_server is free software: you can redistribute it and/or modify
#   it under the terms of the GNU Affero General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   jasper_server is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU Affero General Public License for more details.
#
#   You should have received a copy of the GNU Affero General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp.osv import osv, fields
from common import registered_report
import logging
import importlib
from openerp.report import report_sxw
import openerp.netsvc as netsvc
import openerp.modules as addons

import openerp
from openerp import models, fields
import logging
from jasper import report_jasper

_logger = logging.getLogger(__name__)


class IrActionReport(models.Model):
    _inherit = 'ir.actions.report.xml'

    report_type = fields.Selection(selection_add=[('jasper', 'Jasper')])

    def register_all(self, cursor, called_from_jasper_server_webkit=False):
        
        return_value = super(IrActionReport, self).register_all(cursor)

        # in case jasper_server_webkit is installed, it will do all,
        # to make sure, that it is done after all webkit reports are installed
        loaded_mods = addons.module.loaded
        if 'jasper_server_webkit' in loaded_mods:
            return return_value

        _logger.info('====[REGISTER JASPER REPORT]========================')
        cursor.execute("""SELECT id, report_name
                            FROM ir_act_report_xml
                           WHERE report_type = 'jasper'""")
        records = cursor.dictfetchall()
        for record in records:
            registered_report(record['report_name'])
        _logger.info('====[END REGISTER JASPER REPORT]====================')

        _logger.info('====[REGISTER RML REPORT FOR JASPER REPORT]========================')
        cursor.execute("""
          SELECT ir_act_report_xml.id, ir_act_report_xml.report_name
            FROM ir_act_report_xml, jasper_document
            WHERE jasper_document.mode='rml'
              AND jasper_document.rml_ir_actions_report_xml_id = ir_act_report_xml.id""")
        records = cursor.dictfetchall()
        for record in records:

            gname = 'report.' + record['report_name']
            if gname in netsvc.Service._services:

                # first rename the original report
                gname_new = 'report.rml2jasper.' + record['report_name']
                netsvc.Service._services[gname_new] = netsvc.Service._services[gname]
                del netsvc.Service._services[gname]

                # register the new jasper report
                registered_report(record['report_name'])
                _logger.info('Register the jasper report service [%s]' % record['report_name'])

        _logger.info('====[END REGISTER RML REPORT FOR JASPER REPORT]====================')

        return return_value
# 
#     @classmethod
#     def _add_field(self, name, field):
#         res = super(IrActionReport, self)._add_field(name, field)
# 
#         if name == 'report_type':
#             if 'jasper' not in zip(*field.selection)[0]:
#                 field.selection.append(('jasper', 'Jasper'))
# 
#         return res


    def _lookup_report(self, cr, name):
        """
        Look up a report definition.
        """
        # First lookup in the deprecated place, because if the report definition
        # has not been updated, it is more likely the correct definition is there.
        # Only reports with custom parser specified in Python are still there.
        if 'report.' + name in openerp.report.interface.report_int._reports:
            new_report = openerp.report.interface.report_int._reports['report.' + name]
            if not isinstance(new_report, report_jasper):
                new_report = None
        else:
            cr.execute("SELECT * FROM ir_act_report_xml WHERE report_name=%s and report_type=%s", (name, 'jasper'))
            r = cr.dictfetchone()
            if r:
                new_report = report_jasper('report.'+r['report_name'])
            else:
                new_report = None

        if new_report:
            return new_report
        else:
            return super(IrActionReport, self)._lookup_report(cr, name)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
