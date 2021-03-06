# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
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

import os
import re

from lxml import etree
import netsvc
import pooler

import tools
import addons
import print_xml
import render
import urllib

#
# encode a value to a string in utf8 and converts XML entities
#
def toxml(val):
    if isinstance(val, str):
        str_utf8 = val
    elif isinstance(val, unicode):
        str_utf8 = val.encode('utf-8')
    else:
        str_utf8 = str(val)
    return str_utf8.replace('&', '&amp;').replace('<','&lt;').replace('>','&gt;')

class report_int(netsvc.Service):
    def __init__(self, name, audience='*'):
        assert not self.exists(name), 'The report "%s" already exists!' % name
        super(report_int, self).__init__(name, audience)
        if name[0:7]<>'report.':
            raise Exception, 'ConceptionError, bad report name, should start with "report."'
        self.name = name
        self.id = 0
        self.name2 = '.'.join(name.split('.')[1:])
        self.title = None
        #self.joinGroup('report')
        self.exportMethod(self.create)

    def create(self, cr, uid, ids, datas, context=None):
        return False

"""
    Class to automatically build a document using the transformation process:
        XML -> DATAS -> RML -> PDF
                            -> HTML
    using a XSL:RML transformation
"""
class report_rml(report_int):
    def __init__(self, name, table, tmpl, xsl):
        super(report_rml, self).__init__(name)
        self.table = table
        self.tmpl = tmpl
        self.xsl = xsl
        self.bin_datas = {}
        self.generators = {
            'pdf': self.create_pdf,
            'html': self.create_html,
            'raw': self.create_raw,
            'sxw': self.create_sxw,
            'txt': self.create_txt,
            'odt': self.create_odt,
            'html2html' : self.create_html2html,
            'makohtml2html' :self.create_makohtml2html,
        }

    def create(self, cr, uid, ids, datas, context):
        xml = self.create_xml(cr, uid, ids, datas, context)
        xml = tools.ustr(xml).encode('utf8')
        report_type = datas.get('report_type', 'pdf')
        if report_type == 'raw':
            return (xml,report_type)
        rml = self.create_rml(cr, xml, uid, context)
        pool = pooler.get_pool(cr.dbname)
        ir_actions_report_xml_obj = pool.get('ir.actions.report.xml')
        report_xml_ids = ir_actions_report_xml_obj.search(cr, uid, [('report_name', '=', self.name[7:])], context=context)
        self.title = report_xml_ids and ir_actions_report_xml_obj.browse(cr,uid,report_xml_ids)[0].name or 'OpenERP Report'
        create_doc = self.generators[report_type]
        pdf = create_doc(rml, title=self.title)
        return (pdf, report_type)

    def create_xml(self, cr, uid, ids, datas, context=None):
        if not context:
            context={}
        doc = print_xml.document(cr, uid, datas, {})
        self.bin_datas.update( doc.bin_datas  or {})
        doc.parse(self.tmpl, ids, self.table, context)
        xml = doc.xml_get()
        doc.close()
        return self.post_process_xml_data(cr, uid, xml, context)

    def post_process_xml_data(self, cr, uid, xml, context=None):
        if not context:
            context={}
        # find the position of the 3rd tag
        # (skip the <?xml ...?> and the "root" tag)
        iter = re.finditer('<[^>]*>', xml)
        i = iter.next()
        i = iter.next()
        pos_xml = i.end()

        doc = print_xml.document(cr, uid, {}, {})
        tmpl_path = addons.get_module_resource('base', 'report', 'corporate_defaults.xml')
        doc.parse(tmpl_path, [uid], 'res.users', context)
        corporate_header = doc.xml_get()
        doc.close()

        # find the position of the tag after the <?xml ...?> tag
        iter = re.finditer('<[^>]*>', corporate_header)
        i = iter.next()
        pos_header = i.end()

        return xml[:pos_xml] + corporate_header[pos_header:] + xml[pos_xml:]

    #
    # TODO: The translation doesn't work for "<tag t="1">textext<tag> tex</tag>text</tag>"
    #
    def create_rml(self, cr, xml, uid, context=None):
        if not context:
            context={}
        pool = pooler.get_pool(cr.dbname)
        ir_translation_obj = pool.get('ir.translation')

        # In some case we might not use xsl ...
        if not self.xsl:
            return xml

        stylesheet = etree.parse(tools.file_open(self.xsl))
        xsl_path, _ = os.path.split(self.xsl)
        for import_child in stylesheet.findall('./import'):
            if 'href' in import_child.attrib:
                imp_file = import_child.get('href')
                _, imp_file = tools.file_open(imp_file, subdir=xsl_path, pathinfo=True)
                import_child.set('href', urllib.quote(str(imp_file)))

        #TODO: get all the translation in one query. That means we have to:
        # * build a list of items to translate,
        # * issue the query to translate them,
        # * (re)build/update the stylesheet with the translated items

        def translate(doc, lang):
            for node in doc.xpath('//*[@t]'):
                translation = ir_translation_obj._get_source(cr, uid, self.name2, 'xsl', lang, node.text)
                if translation:
                    node.text = translation

        if context.get('lang', False):
            translate(stylesheet, context['lang'])

        transform = etree.XSLT(stylesheet)
        xml = etree.tostring(
            transform(etree.fromstring(xml)))

        return xml

    def create_pdf(self, rml, localcontext = None, logo=None, title=None):
        if logo:
            self.bin_datas['logo'] = logo
        else:
            if 'logo' in self.bin_datas:
                del self.bin_datas['logo']
        obj = render.rml(rml, localcontext, self.bin_datas, tools.config['root_path'],title)
        obj.render()
        return obj.get()

    def create_html(self, rml, localcontext = None, logo=None, title=None):
        obj = render.rml2html(rml, localcontext, self.bin_datas)
        obj.render()
        return obj.get()

    def create_txt(self, rml,localcontext, logo=None, title=None):
        obj = render.rml2txt(rml, localcontext, self.bin_datas)
        obj.render()
        return obj.get().encode('utf-8')

    def create_html2html(self, rml, localcontext = None, logo=None, title=None):
        obj = render.html2html(rml, localcontext, self.bin_datas)
        obj.render()
        return obj.get()


    def create_raw(self,rml, localcontext = None, logo=None, title=None):
        obj = render.odt2odt(etree.XML(rml),localcontext)
        obj.render()
        return etree.tostring(obj.get())

    def create_sxw(self,rml,localcontext = None):
        obj = render.odt2odt(rml,localcontext)
        obj.render()
        return obj.get()

    def create_odt(self,rml,localcontext = None):
        obj = render.odt2odt(rml,localcontext)
        obj.render()
        return obj.get()

    def create_makohtml2html(self,html,localcontext = None):
        obj = render.makohtml2html(html,localcontext)
        obj.render()
        return obj.get()

from report_sxw import report_sxw

def register_all(db):
    opj = os.path.join
    cr = db.cursor()
    cr.execute("SELECT * FROM ir_act_report_xml WHERE auto=%s ORDER BY id", (True,))
    result = cr.dictfetchall()
    cr.close()
    svcs = netsvc.Service._services
    for r in result:
        if svcs.has_key('report.'+r['report_name']):
            continue
        if r['report_rml'] or r['report_rml_content_data']:
            report_sxw('report.'+r['report_name'], r['model'],
                    opj('addons',r['report_rml'] or '/'), header=r['header'])
        if r['report_xsl']:
            report_rml('report.'+r['report_name'], r['model'],
                    opj('addons',r['report_xml']),
                    r['report_xsl'] and opj('addons',r['report_xsl']))


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
