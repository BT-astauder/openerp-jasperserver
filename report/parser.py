# -*- coding: utf-8 -*-
##############################################################################
#
#    jasper_server module for OpenERP, 
#    Copyright (C) 2010 SYLEAM Info Services (<http://www.syleam.fr/>) 
#              Christophe CHAUVET
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

from cStringIO import StringIO
from HTMLParser import HTMLParser

class HTML2Text(HTMLParser):
    def __init__(self):
        HTMLParser.__init__(self)
        self.output = StringIO()
        self.is_valid = True
        self.is_linefeed = True
        self.is_title = True
    def get_text(self):
        return self.output.getvalue()
    def handle_data(self, data):
        if not self.is_valid:
            self.output.write(data)
        if self.is_linefeed:
            self.output.write('\n')
        elif self.is_title:
            self.output.write('\n')
    def handle_starttag(self, tag, attrs):
        if tag == "body":
            self.is_valid = False
        elif tag == 'p':
            self.is_linefeed = False
        elif tag.startswith('h'):
            self.is_title = False
    def handle_endtag(self, tag):
        if tag == "body":
            self.is_valid = True
        elif tag == 'p':
            self.is_linefeed = True
        elif tag.startswith('h'):
            self.is_title = True

def ParseHTML(source):
    p = HTML2Text()
    p.feed(source)
    return p.get_text()

if __name__ == '__main__':
    print ParseHTML("""<html><head><title>Apache Tomcat/5.5.20 - Rapport d'erreur</title>
<style><!--H1 {font-family:Tahoma,Arial,sans-serif;color:white;background-color:#525D76;font-size:22px;} 
           H2 {font-family:Tahoma,Arial,sans-serif;color:white;background-color:#525D76;font-size:16px;} 
           H3 {font-family:Tahoma,Arial,sans-serif;color:white;background-color:#525D76;font-size:14px;} 
           BODY {font-family:Tahoma,Arial,sans-serif;color:black;background-color:white;} 
           B {font-family:Tahoma,Arial,sans-serif;color:white;background-color:#525D76;} 
           P {font-family:Tahoma,Arial,sans-serif;background:white;color:black;font-size:12px;}
           A {color : black;}A.name {color : black;}HR {color : #525D76;}--></style> 
</head><body>
<h1>Etat HTTP 401 - Bad credentials</h1>
<HR size="1" noshade="noshade"><p><b>type</b> Rapport d'état</p>
<p><b>message</b> <u>Bad credentials</u></p><p><b>description</b> 
<u>La requête nécessite une authentification HTTP (Bad credentials).</u></p>
<HR size="1" noshade="noshade"><h3>Apache Tomcat/5.5.20</h3>
</body></html>""")

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
