# -*- coding: utf-8 -*-
##############################################################################
#
#    jasper_server module for OpenERP,
#    Copyright (C) 2014 Mirounga (<http://www.mirounga.fr/>)
#                            Christophe CHAUVET <christophe.chauvet@gmail.com>
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
from base64 import decodestring


class LoadFile(models.TransientModel):
    _name = 'load.jrxml.file'
    _description = 'Load file in the jasperdocument'

    name = fields.Char('File Name')
    datafile = fields.Binary('File', required=True,
                             help='Select file to transfer')
    save_as_attachment = fields.Boolean("Save file as attachment")

    @api.multi
    def import_file(self):

        self.ensure_one()
        content = decodestring(self.datafile)
        self.env['jasper.document'].browse(self._context.get('active_ids')).parse_jrxml(content, self.save_as_attachment)

        return True
