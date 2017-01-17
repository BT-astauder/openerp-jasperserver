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

from odoo import fields, models


class JasperDocumentParameter(models.Model):
    _name = 'jasper.document.parameter'
    _description = 'Add parameter to send to jasper server'

    name = fields.Char('Name', size=32, help='Name of the jasper parameter, the prefix must be OERP_', required=True)
    code = fields.Char('Code', size=256, help='Enter the code to retrieve data', required=True)
    enabled = fields.Boolean('Enabled', default=True)
    document_id = fields.Many2one('jasper.document', 'Document', required=True, ondelete='cascade')
