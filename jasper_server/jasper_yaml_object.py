# b-*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2013 brain-tec AG (http://www.brain-tec.ch) 
#    All Right Reserved
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

from openerp.osv import osv, fields

class jasper_yaml_object(osv.osv):
    """(NULL)"""
    _name = 'jasper.yaml_object'
        
    _columns = {
        'type'  : fields.selection([("yaml", "YAML"), ("sxw", "SXW")], string="Type of record", required=True),
        'jasper_document_id': fields.many2one('jasper.document', string="Jasper Document"),
        'name': fields.char('Name', size=50, required=True),
        'model': fields.many2one('ir.model', string='Model'),
        'domain': fields.char('Domain', size=128),
        'offset': fields.integer('Offset'),
        'limit': fields.integer('Limit'),
        'order': fields.char('Order', size=128),
        'fields': fields.text('Fields in YAML'),

        'ir_actions_report_xml_id': fields.many2one('ir.actions.report.xml', string="Link to RML report, that generates the XML"),

        # 'report_sxw_name': fields.char('Report SXW Name', help='e.g. report.account.general.ledger_landscape'), # report_name
        # 'report_sxw_table': fields.char('Report SXW Table', help="e.g. account.account"), # model
        # 'report_sxw_rml': fields.char('Path to the RML', help="e.g. addons/account/report/account_general_ledger_landscape.rml"), # report_file
        # 'report_sxw_parser': fields.char('Parser for the SXW report', help="e.g. account.report.account_general_ledger.general_ledger"),
        # 'report_swx_header': fields.char('Header for the SXW report', help="e.g. internal landscape"),

    }