# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution    
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import wizard
import pooler
import time
from tools.translate import _

_form = '''<?xml version="1.0"?>
    <form string="Харилцагч бүртгэх">
        <field name="partner_type" required="1" />
        <field name="is_new" required="1"/>
        <field name="ref" />
        <field name="register_id" />
    </form>'''

_fields = {
    'partner_type': {'string': 'Харилцагчийн төрөл', 'type': 'selection','selection':[('person','Иргэн харилцагч'),('corp','Хуулийн этгээд харилцагч')],'default':'person'},
    'is_new': {'string':'Өмнө нь үйлчлүүж байсан эсэх','type':'selection','selection':[('new','Шинэ харилцагч'),('old','Давтан харилцагч')],'default': 'new'},
    'register_id': {'string':'Регистерийн дугаар','type': 'char','size':'64'},
    'ref': {'string':'Харилцагчийн ID','type': 'char','size':'64'},

}

      
def _open_window(self, cr, uid, data, context):
    if data['form']['partner_type'] == 'person':
         cr.execute('select id,name from ir_ui_view where name=%s and type=%s', ('view.xac.partner.person.form', 'form'))
         view_form = cr.fetchone()[0]
         cr.execute('select id,name from ir_ui_view where name=%s and type=%s', ('view.xac.partner.person.tree', 'tree'))
         view_tree = cr.fetchone()[0]
         res = {
                    'name': 'Харилцагчийн бүртгэл (Иргэн)',
                    'view_type': 'form',
                    "view_mode": 'tree,form',
                    'res_model':'xac.partner',
                    'type': 'ir.actions.act_window',
                    'views': [(view_tree,'tree'), (view_form,'form')],
                    'view_id': False
         }
         if data['form']['is_new'] == 'new':
             res['views'] = [(view_form,'form'),(view_tree,'tree')]
             return res
         else:
             domain = []
             if data['form'].get('ref',False) and len(data['form']['ref']) > 0:
                domain.append(('ref','like',data['form']['ref']))
             if data['form'].get('register_id',False) and len(data['form']['register_id']) > 0:
                domain.append(('register_id','like',data['form']['register_id']))
             res['domain'] = str(domain) 
             return res

class wizard_register_partner(wizard.interface):
    states = {
        'init': {
            'actions': [],
            'result': {'type': 'form', 'arch':_form, 'fields':_fields, 'state': [('end', 'Болих','gtk-cancel'),('open', 'Бүртгэх','gtk-ok')]}
        },
        'open': {
            'actions': [],
            'result': {'type': 'action', 'action': _open_window, 'state':'end'}
        }
    }
wizard_register_partner('wizard.partner.register')
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
