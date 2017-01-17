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


class jasper_document_label(models.Model):
    _name = 'jasper.document.label'
    _description = 'Manage label in document, for different language'

    name = fields.Char('Parameter', size=64,
                       help='Name of the parameter sent to JasperServer, prefix with I18N_\n'
                            'eg: test becomes I18N_TEST as parameter', required=True)
    value = fields.Char('Value', size=256, required=True, translate=True,
                        help='Name of the label, this field must be translated in all '
                             'languages available in the database')
    document_id = fields.Many2one('jasper.document', 'Document', required=True, ondelete='cascade')
    enabled = fields.Boolean('Enabled', default=True)
