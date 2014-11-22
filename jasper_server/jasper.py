# -*- coding: utf-8 -*-
##############################################################################
#
#    jasper_server module for OpenERP,
#    Copyright (C) 2009-2011 SYLEAM Info Services (<http://www.syleam.fr/>)
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

from openerp.report.interface import report_int
from openerp.osv.osv import except_osv

import openerp.pooler as pooler
import openerp.netsvc as netsvc
import sys
import openerp.exceptions
import openerp.tools as tools


from report.report_soap import Report
from report.report_exception import JasperException

import logging

_logger = logging.getLogger(__name__)


class report_jasper(report_int):
    """
    Extend report_int to use Jasper Server
    """

    def create(self, cr, uid, ids, data, context=None):
        if context is None:
            context = {}

        # WORKS
        # from account.report.account_general_ledger import general_ledger
        # # account_analytic_journal = general_ledger(cr, uid, 'dummy', context=context)
        #
        # mydata = data.copy()
        # mydata['report_type'] = 'raw'
        # from openerp.report import report_sxw
        # report = report_sxw.report_sxw('report.account.general.ledger_landscape2',
        #                                'account.account',
        #                                'addons/account/report/account_general_ledger_landscape.rml',
        #                                parser=general_ledger,
        #                                header='internal landscape')
        # function = report.create(cr, uid, ids, mydata, context=None)
        # WORKS END


        # cr = pooler.get_db(cr.dbname).cursor()
        # try:
        #     gname = 'report.'+ "account.general.ledger_landscape2"
        #     if gname in netsvc.Service._services:
        #         return
        #     obj = netsvc.LocalService(gname)
        #     mydata = data.copy()
        #     mydata['report_type'] = 'raw'
        #     (result, format) = obj.create(cr, uid, ids, mydata, context)
        #     if not result:
        #         tb = sys.exc_info()
        #         self._reports[id]['exception'] = openerp.exceptions.DeferredException('RML is not available at specified location or not enough data to print!', tb)
        #     self._reports[id]['result'] = result
        #     self._reports[id]['format'] = format
        #     self._reports[id]['state'] = True
        # except Exception, exception:
        #     _logger.exception('Exception: %s\n', exception)
        #     if hasattr(exception, 'name') and hasattr(exception, 'value'):
        #         self._reports[id]['exception'] = openerp.exceptions.DeferredException(tools.ustr(exception.name), tools.ustr(exception.value))
        #     else:
        #         tb = sys.exc_info()
        #         self._reports[id]['exception'] = openerp.exceptions.DeferredException(tools.exception_to_unicode(exception), tb)
        #     self._reports[id]['state'] = True
        # cr.commit()
        # cr.close()
        #
        # ###################
        # if node.extension != '.pdf':
        #     raise Exception("Invalid content: %s" % node.extension)
        # report = self.pool.get('ir.actions.report.xml').browse(cr, uid, node.report_id, context=context)
        # srv = netsvc.Service._services['report.'+report.report_name]
        # ctx = node.context.context.copy()
        # ctx.update(node.dctx)
        # pdf,pdftype = srv.create(cr, uid, [node.act_id,], {}, context=ctx)
        # #####################



        if not context:
            context={}

        # rml_parser = self.parser(cr, uid, self.name2, context=context)
        # objs = self.getObjects(cr, uid, ids, context)
        # rml_parser.set_context(objs, data, ids, report_xml.report_type)
        # processed_rml = etree.XML(rml)
        # processed_rml = self.preprocess_rml(processed_rml, report_xml.report_type)
        # data.get('report_type', 'pdf')



        if _logger.isEnabledFor(logging.DEBUG):
            _logger.debug('Call %s' % self.name)
        try:
            return Report(self.name, cr, uid, ids, data, context).execute()
        except JasperException, e:
            raise except_osv(e.title, e.message)

report_jasper('report.print.jasper.server')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
