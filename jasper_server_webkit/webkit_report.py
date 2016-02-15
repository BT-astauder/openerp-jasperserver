# b-*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2015 brain-tec AG (http://www.brain-tec.ch)
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

from report_webkit.webkit_report import WebKitParser
import tools

original_generate_pdf = WebKitParser.generate_pdf

def generate_pdf(self, comm_path, report_xml, header, footer, html_list,
                 webkit_header=False, printer=False, child=False,
                 context=None):
    if 'called_from_jasper' in context:
        return tools.ustr("\n".join(html_list))

    return original_generate_pdf(self, comm_path, report_xml, header, footer,
                                 html_list, webkit_header, printer, child,
                                 context)

WebKitParser.generate_pdf = generate_pdf