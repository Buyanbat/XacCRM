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
from base64 import decode

def _open_window(self, cr, uid, data, context):
    if data.get('id', False):
         partner = pooler.get_pool(cr.dbname).get('xac.partner').browse(cr,uid,data['id'])
         cr.execute('select id,name from ir_ui_view where name=%s and type=%s', ('view.loan.draft.form', 'form'))
         view_form = cr.fetchone()[0]
         cr.execute('select id,name from ir_ui_view where name=%s and type=%s', ('view.loan.draft.tree', 'tree'))
         view_tree = cr.fetchone()[0]
         
         ref = partner.ref
         if isinstance(ref,unicode):
            ref = ref.encode('utf-8')
         
         res = {
                    'name': 'Зээлийн Бүтээгдэхүүн тодорхойлох - %s '%(ref),
                    'view_type': 'form',
                    "view_mode": 'tree,form',
                    'res_model':'loan.draft',
                    'type': 'ir.actions.act_window',
                    'views': [(view_tree,'tree'), (view_form,'form')],
                    'view_id': False,
                    'context': "{'partner_id': '%s'}"%data['id'],
         }
         domain = []
         domain.append(('partner_id','=',data['id']))
         res['domain'] = str(domain) 
         if len(partner.loans) == 0:
             res['views'] = [(view_form,'form'),(view_tree,'tree')]
         return res
    else:
        return False
# Зээлийн бүтээгдэхүүн тодорхойлох
class wizard_partner_loan(wizard.interface):
    states = {
        'init': {
            'actions': [],
            'result': {'type': 'action', 'action': _open_window, 'state':'end'}
        }
    }
wizard_partner_loan('wizard.partner.loan')
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
