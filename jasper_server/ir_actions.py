# -*- coding: utf-8 -*-
##############################################################################
#
#    jasper_server module for OpenERP, Management module for Jasper Server
#    Copyright (C) 2011 SYLEAM (<http://www.syleam.fr/>)
#              Christophe CHAUVET <christophe.chauvet@syleam.fr>
#
#    This file is a part of jasper_server
#
#    jasper_server is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    jasper_server is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp.osv import osv
from jasper_server.common import registered_report
import logging
import importlib
from openerp.report import report_sxw


_logger = logging.getLogger(__name__)


class IrActionReport(osv.Model):
    _inherit = 'ir.actions.report.xml'

    def register_all(self, cursor):
        """
        Register all jasper report
        """
        _logger.info('====[REGISTER JASPER REPORT]========================')
        cursor.execute("SELECT id, report_name FROM ir_act_report_xml WHERE report_type = 'jasper'")
        records = cursor.dictfetchall()
        for record in records:
            registered_report(record['report_name'])
        _logger.info('====[END REGISTER JASPER REPORT]====================')

        _logger.info('====[REGISTER RML REPORT FOR JASPER REPORT]========================')
        # cursor.execute("SELECT id, report_name FROM jasper_yaml_object WHERE report_type = 'jrml'")
        # records = cursor.dictfetchall()
        # for record in records:


#        parser_module = importlib.import_module('account.report.account_general_ledger')
#        parser_class = getattr(parser_module, 'general_ledger')

        # from account.report.account_general_ledger import general_ledger
#        report_sxw.report_sxw('report.account.general.ledger_landscape2',
#                                   'account.account',
#                                   'addons/account/report/account_general_ledger_landscape.rml',
#                                   parser=parser_class,
#                                   header='internal landscape')

        _logger.info('====[END REGISTER RML REPORT FOR JASPER REPORT]====================')

        return True


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
