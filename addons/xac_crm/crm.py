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
import time

class partner_reason(osv.osv):
    _name = "partner.reason"
    _description = "Хас Банкинд хандсан шалтгаан"
    _columns = {
                'name': fields.char(u'Ner',size=128,required=True),
                'note': fields.text(u'Tailbar')
    }
partner_reason()

class xac_service(osv.osv):
    _name = "xac.service"
    _description = "Хас Банкны үзүүлэх үйлчилгээ"
    _columns = {
                'name': fields.char(u'Ner',size=128,required=True),
                'note': fields.text(u'Tailbar'),
                'isservice':fields.boolean('Hariltsagchid sanal bolgoh eseh',
                                           help="Зээлийн өргөдөл бүртгэх үед Санал болгох бсад үйлчилгээ хэсэгт харагдах эсэх") 
    }
xac_service()

class xac_partner(osv.osv):
    _name = "xac.partner"
    _description = "Харилцагчид"
    _columns = {
        # For Global fields
        'ref': fields.char('Hariltsagchiin ID',size=128),
        'reasons': fields.one2many('partner.reason.log','partner_id','XacBankind handsan shaltgaan'),
        'services': fields.one2many('xac.service.log','partner_id',u'Banknaas yamar uilchilgee avahiig husch bna'),
        'loans': fields.one2many('loan.draft','partner_id','Zeeliin orgodluud'),
        'state': fields.selection([ ('person','Иргэн'),
                                    ('company','Аж ахуйн нэгж'),
                                    ('employeer','Банкны Ажилтан'),
                                    ('ngo','ТББ'),
                                    ('scc','ХЗХ'),
                                    ('other','Бусад')],'Hariltsagchiin torol',readonly=True),
        'name': fields.char(u'Ner',size=64),
        'addresses': fields.one2many('partner.address','partner_id','Hariltsagchiin hayag'),
        'phones': fields.one2many('partner.phone','partner_id','Hariltsagchiin utas'),
        #For Person
        'register_id': fields.char(u'Registeriin dugaar',size=10),
        'civil_id': fields.char('Irgenii unemlehiin dugaar',size=9),
        'parent_name':fields.char('Etseg(eh) - iin ner',size=64),
        'gender': fields.selection([('male','Эрэгтэй'),('female','Эмэгтэй')],u"Huis"),
        'bdate': fields.date('Torson ognoo'),
        # For Company
        'public_id': fields.char(u'Ulsiin burgeliin dugaar',size=12),
        'made_date': fields.date(u'Baiguulagdsan ognoo'),
        'direction': fields.char(u'Uil ajillagaanii chiglel',size=128),
        
    }
    
    _defaults = {
            'gender': lambda *a: 'male',
            'bdate': lambda *a: '1900-01-31'
    }
    
    
    def onchange_register_id(self,cr,uid,ids,register_id):
        if isinstance(register_id,str):
            letters = register_id[1]
            
        return {'value': {'ref': register_id}}
    def create(self,cr,uid,vals,context={}):
        if vals.get('register_id',False):
            vals['ref'] = vals['register_id']
        return super(xac_partner, self).create(cr, uid, vals, context)
    def write(self,cr,uid,ids,vals,context={}):
        if vals.get('register_id',False):
            vals['ref'] = vals['register_id']
        return super(xac_partner, self).write(cr, uid, ids,vals, context)
xac_partner()

class partner_reason_log(osv.osv):
    _name = "partner.reason.log"
    _description = "Хас банкинд хандсан шалтгаанууд"
    _columns = {
                'branch_id': fields.many2one('xac.branch','Salbar'),
                'reason_id': fields.many2one('partner.reason','Shaltgaan'),
                'partner_id': fields.many2one('xac.partner',u'Hariltsagch(Irgen)'),
                'date': fields.date('Ognoo'),
                'note': fields.text('Temdeglel'),
                
    }
    
   # def _get_branch(self,cr,uid,context={}):
    #    curr_user = self.pool.get('res.users').browse(cr,uid,uid)
     #   return curr_user.branches[0].id 
       
    _defaults = {
        'date': lambda *a: time.strftime("%Y-%m-%d"),
       # 'branch_id': _get_branch,
    }
partner_reason_log()

class xac_service_log(osv.osv):
    _name = "xac.service.log"
    _desciption = "Хас Банкнаас авах үйлчилгээ"
    _columns = {
         'branch_id': fields.many2one('xac.branch','Salbar'),
         'service_id': fields.many2one('xac.service','Uilchilgee'),
         'partner_id': fields.many2one('xac.partner',u'Hariltsagch(Irgen)'),
         'date': fields.date('Ognoo'),
         'note': fields.text('Temdeglel'),
         
         'order_id': fields.many2one('loan.order','Orgodol'),
    }
  #  def _get_branch(self,cr,uid,context={}):
  #      curr_user = self.pool.get('res.users').browse(cr,uid,uid)
  #      return curr_user.branches[0].id 
    
    _defaults = {
        'date': lambda *a: time.strftime("%Y-%m-%d"),
   #     'branch_id': _get_branch,
    }
xac_service_log()  

class partner_address(osv.osv):
    _name = "partner.address"
    _description = "Харилцагчийн хаяг"
    _columns = {
        'name': fields.selection([('home','Гэрийн хаяг'),('job','Ажлын хаяг')],'Hayagiin torol', required=True),
        'city':fields.char('Aimag/Hot',size=128),
        'district':fields.char('Sum/Duureg',size=128),
        'street': fields.char('Horoo',size=128),
        'number': fields.char('Bair,toot',size=128),
        'partner_id': fields.many2one('xac.partner','Hariltsagch'),
        'note': fields.text('Delgerengui'),
    }
    
    
partner_address()  

class partner_phone(osv.osv):
    _name = "partner.phone"
    _description = "Харилцагчийн утас"
    _columns = {
        'name': fields.selection([('cellphone','Гар утас'),
                                  ('homephone','Гэрийн утас'),
                                  ('jobphone','Ажлын утас'),
                                  ('other','Бусад')],'Dugaariin torol'),
        'number': fields.char('Utasnii dugaar',size=12),
        'note': fields.text('Delgerengui'),
        'partner_id': fields.many2one('xac.partner','Hariltsagch'),
        
    }
partner_phone()

