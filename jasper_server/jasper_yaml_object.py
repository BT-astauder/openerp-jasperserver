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
        'jasper_document_id': fields.many2one('jasper.document', string="Jasper Document"),
        'name': fields.char('Name', size=50, required=True),
        'model': fields.many2one('ir.model', string='Model', required=True),
        'domain': fields.char('Domain', size=128),
        'offset': fields.integer('Offset'),
        'limit': fields.integer('Limit'),
        'order': fields.char('Order', size=128),
        'context': fields.char('Context',),
        'user_id': fields.many2one('res.users', string='User'),
        'fields': fields.text('Fields in YAML'),
    }