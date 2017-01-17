# -*- coding: utf-8 -*-
##############################################################################
#
#    jasper_server module for OpenERP
#    Copyright (c) 2008-2009 EVERLIBRE (http://everlibre.fr) Eric VERNICHON
#    Copyright (C) 2009-2011 SYLEAM ([http://www.syleam.fr]) Christophe CHAUVET
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
#    along with this program.  If not, see [http://www.gnu.org/licenses/].
#
##############################################################################

{
    'name': 'JasperReport Server Interface',
    'version': '10.0.1.0',
    'category': 'Reporting',
    'sequence': 20,
    'complexity': "expert",
    'description': """This module interface JasperReport Server with Odoo

Features:

- Document source must be in CSV, XML
- Save document as attachment on object
- Retrieve attachment if present
- Launch multiple reports and merge in one printing action
- Add additional parameters (ex from fields function)
- Affect group on report
- Use context to display or not the print button (eg: in stock.picking separate per type)
- Launch report based on SQL View

This module requires some libraries to work properly

- pip install httplib2 (>= 0.6.0)
- pip install pyPdf (>= 1.13)
- pip install python-dime


In collaboration with Eric Vernichon (from Everlibre)

Migrated and improved by Brain Tec.
""",
    'author': 'SYLEAM',
    'website': 'http://www.syleam.fr',
    'images': ['images/accueil.png', 'images/palette.png',
               'images/document_form.png'],
    'external_dependencies': {
        'python': [
            'httplib2',
            'pyPdf',
            'dime',
            'lxml',
            'HTMLParser',
        ],
    },
    'depends': [
        'base',
    ],
    'data': [
        'security/groups.xml',
        'security/ir.model.access.csv',

        'data/jasper_document_extension_data.xml',

        'wizard/load_file_view.xml',

        'views/jasper_document_extension_views.xml',
        'views/jasper_document_label_views.xml',
        'views/jasper_document_parameter_views.xml',
        'views/jasper_server_views.xml',
        'views/jasper_document_views.xml',
        'views/jasper_yaml_object_views.xml',
    ],
    'demo': [
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
}
