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
#########

from osv import fields, osv
from tools import config
from peak.rules.ast_builder import _name

class xac_branch(osv.osv):
    _name = "xac.branch"
    _description = u"Хас Банкны салбарууд"
    
    def _get_full_name(self, cr, uid, ids, name, args, context):
        res = {}
        for m in self.browse(cr, uid, ids, context=context):
            res[m.id] = self._get_one_full_name(m)
        return res

    def _get_one_full_name(self, menu, level=6):
        if level<=0:
            return '...'
        if menu.parent:
            parent_path = self._get_one_full_name(menu.parent, level-1) + "/"
        else:
            parent_path = ''
        return parent_path + menu.name
    _columns = {
        'name': fields.char(u'Salbariin ner',size=128,required=True),
        'parent': fields.many2one('xac.branch',u'Harya salbar'),
        'childs': fields.one2many('xac.branch','parent',u'Ded salbar'),
        'note': fields.text(u'Delgerengui'),
        'director': fields.char('Zahiral',size=128),
        'fullname': fields.function(_get_full_name,type='char',size=128, method=True,string="Buten ner"),
        'users': fields.many2many('res.users','users_branch_rel','branch_id','uid',u'Ajilchid'),

    }
xac_branch()

