# b-*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2016 brain-tec AG (http://www.braintec-group.com)
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

from odoo import api, fields, models


class JasperYamlObject(models.Model):
    """(NULL)"""
    _name = 'jasper.yaml_object'

    jasper_document_id = fields.Many2one('jasper.document', string="Jasper Document")
    name = fields.Char('Name', size=50, required=True)
    model = fields.Many2one('ir.model', string='Model', required=True)
    domain = fields.Char('Domain', size=128)
    offset = fields.Integer('Offset')
    limit = fields.Integer('Limit')
    order = fields.Char('Order', size=128)
    context = fields.Char('Context')
    user_id = fields.Many2one('res.users', string='User')
    fields = fields.Text('Fields in YAML')
