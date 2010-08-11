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
from bsddb.dbtables import _columns
import time

class loan_requirements(osv.osv):
    _name = "loan.requirements"
    _description = "Зээлийн бичиг баримтын бүрдүүлбэр"
    _columns = {
        'name': fields.char('Barimtiin ner',size=128,required=True), # Баримтын нэр
        'note': fields.text('Temdeglel'), # Тайлбар
        'loans': fields.many2many('xac.loan','loan_requirements_rel','loan_id','requirement_id','Shaardagdah zeeluud') #Шаардагдах зээлүүд
    }
loan_requirements()

class loan_requirements_log(osv.osv):
    _name = "loan.requirements.log"
    _desctiption = "Зээлийн бичиг баримтын бүрдүүлбэр"
    _columns = {
        'requirement_id': fields.many2one('loan.requirements','Barimt'), #Баримт
        'done': fields.boolean('Buren eseh'), # Бүрэн эсэх
        'order_id': fields.many2one('loan.order','Zeeliin orgodol'), #Өргөдөл
        'date': fields.date('Burduulsen ognoo'), #Бүрдүүлсэн огноо
    }
loan_requirements_log()

class loan_draft(osv.osv):
    _name = "loan.draft"
    _description = "Зээлийн бүтээгдэхүүн тодорхойлох"
         
    def _get_loan_type(self,cr,uid,ids,fields,args,context={},query=''):
        res = {}
        for loan in self.browse(cr,uid,ids):
            res[loan.id] = ''
            if loan.for_own:
               res[loan.id] = u"Хувийн болон өрхийн хэрэглээнд"
            elif loan.for_bussines:
               res[loan.id] = u"Бизнестээ"
        return res
           
    _columns = {
        'loan_type': fields.function(_get_loan_type, type='char', string="Zeeliin zoriulalt",size=64,method=True), #Зээлийн хэрэгцээ
        'partner_id': fields.many2one('xac.partner','Hariltsagch'), # Харилцагч
        
        'for_own': fields.boolean('Huviin bolon orhiin heregtseend'), 
        'for_business': fields.boolean('Biznest'),
        'amount': fields.float('Hussen zeeliin hemjee',required=True),
        'time': fields.integer(' Zeeliin hugatsaa (Saraar)',required=True),
        'velocity': fields.integer('Banknaas avch bui hed deh zeel',required=True),
        'currency': fields.selection([('mnt','Төгрөг'),('usd','Доллар')],'Currency'),
        'usage': fields.selection([('ok','OK'),('no','NO')],'Loan Usage',required=True),
        'telephone': fields.char('Holboo barih utas',size=128),
        'other_usage': fields.char('Busad zoriulalt',size=128),

        'manager_id': fields.many2one('res.users','Hariutsah zeeliin mergejilten'),
        'loans':fields.many2many('xac.loan','xacloan_partnerloan_rel','partner_id','loan_id','Zeeliin medeelel'),
        'family_cap': fields.integer('Am bul'),
        'family_income': fields.integer('Orlogotoi'),
        
        # Тухайн зээлийн мэдээлэл
        'name_for_loan': fields.char('Sanhuugiin tureeseer avah baraa buteegdehuunii ner',size=128),
        'address_for_loan': fields.char('Oron suuts, hashaa baishnii bairshil,hayg',size=128),
        'school_of_student': fields.char('Oyutnii zeeliin huvid suraltsdag surguuli',size=128),
        'company_for_loan': fields.char('Baraa avahaar songoson baiguullaga',size=128),
        'commend': fields.char('Zuuchluulsan baiguullaga',size=128),
        'prepay_of_loan': fields.float('Uridchilgaa tolbor'),
        'is_vitanna': fields.boolean('Vitanna zeeldegch eseh'),
        'is_eko': fields.boolean('Eko zeel eseh'),
        
        # Харилцагчийн Орлогын мэдээлэл
        'personal_incomes': fields.one2many('loan.income.personal','draft_id','Ooriin orlogo'),
        'other_incomes': fields.one2many('loan.income.other','draft_id','Busad orlogo'),
        'family_incomes': fields.one2many('loan.income.family','draft_id','Ger buliin orlogo'),
        
        # Барьцаа хөрөнгийн мэдээлэл
        'moveable_sureties': fields.one2many('loan.surety.moveable','draft_id','Hodloh horongo'),
        'unmoveable_sureties': fields.one2many('loan.surety.unmoveable','draft_id','Ul hodloh horongo'),
        'thirdparty_sureties': fields.one2many('loan.surety.thirdparty','draft_id','Guravdagch etgeediin horongo'),
        
    }
    
    def _get_partners(self,cr,uid,context={}):
        if context.get('partner_id',False):
            return context['partner_id']
        return False
    
    _defaults = {
        'for_own': lambda *a: True,
        'velocity': lambda *a: 1,
        'partner_id': _get_partners,
    }
loan_draft()


# Орлогын мэдээлэл
class loan_income_personal(osv.osv):
    _name = "loan.income.personal"
    _description = "Өөрийн орлого"
    _columns = {
        'type': fields.selection([('bussines','Бизнесийн'),('salary','Цалингийн')],'Orlogiin torol',required=True),
        'company': fields.char('Baiguullaga',size=128,required=True),
        'amount': fields.float('Orlogiin hemjee',required=True),
        'draft_id': fields.many2one('loan.draft','Zeeliin buteegdehuun'),
        'note': fields.text('Temdeglel'),
    }

loan_income_personal()

class loan_income_other(osv.osv):
    _name = "loan.income.other"
    _description = "Бусад орлого"
    _columns = {
        'source': fields.char('Yunaas',size=128,required=True),
        'amount': fields.float('Orlogiin hemjee',required=True),
        'velocity':fields.integer('Davtamj',required=True),
        'draft_id': fields.many2one('loan.draft','Zeeliin buteegdehuun'),
        'note': fields.text('Temdeglel'),

    }
loan_income_other()

class loan_income_family(osv.osv):
    _name = "loan.income.family"
    _description = "Гэр бүлийн орлого"
    _columns = {
        'name': fields.char('Ovog,Ner',size=128),
        'relation': fields.char('Tanii hen boloh',size=128),
        'type': fields.selection([('bussines','Бизнесийн'),('salary','Цалингийн')],'Orlogiin torol',required=True),
        'amount': fields.float('Sariin dundaj orlogo'),
        'draft_id': fields.many2one('loan.draft','Zeeliin buteegdehuun'),
        'note': fields.text('Temdeglel'),

    }
loan_income_family()


# Баталгаа барьцааны мэдээлэл

class loan_surety_moveable(osv.osv):
    _name = "loan.surety.moveable"
    _description = "Хөдлөх хөрөнгө"
    _columns = {
        'type': fields.selection([('car','Машин'),
                                  ('electron','Цахилгаан бараа'),
                                  ('salary','Цалин'),
                                  ('savings','Хадгаламж')],'Барьцаа хөрөнгийн төрөл'),
        'ref': fields.char('Mark,Seri,Dugaar',size=128),
        'owner': fields.char('Henii omch boloh',size=128),
        'made_date': fields.date('Uildverlesen ognoo'),
        'location': fields.char('Bairshil',size=128),
        'amount': fields.float('Zeeldegchiin unelgee'),
        'note': fields.text('Temdegelel'),      
        'draft_id': fields.many2one('loan.draft','Zeeliin buteegdehuun'),

    }
    
loan_surety_moveable() 
class loan_surety_unmoveable(osv.osv):
    _name = "loan.surety.unmoveable"
    _description = "Үл хөдлөх хөрөнгө"
    _columns = {
        'type': fields.selection([('','Орон сууц'),
                                  ('electron','Хашаа байшин')],'Bairtsaa horongiin torol'),
        'ref': fields.char('Gerchilgeenii dugaar,ulsiin burtgel',size=128),
        'owner': fields.char('Henii omch boloh',size=128),
        'made_date': fields.date('Ashiglaltand orson ognoo'),
        'location': fields.char('Bairshil',size=128),
        'amount': fields.float('Zeeldegchiin unelgee'),  
        'note': fields.text('Temdegelel'),
        'draft_id': fields.many2one('loan.draft','Zeeliin buteegdehuun'),

    }
    
loan_surety_unmoveable() 

class loan_surety_thirdparty(osv.osv):
    _name = "loan.surety.thirdparty"
    _description = "Гурав дагч этгээдийн хөрөнгө"
    _columns = {
        'name': fields.char('Ovog, Ner',size=128),
        'relation': fields.char('Tanii hen boloh',size=128),
        'job': fields.char('Ajil, surguuli',size=128),
        'address': fields.char('Geriin hayag',size=128),
        'telephone': fields.char('Utas',size=128),
        'note': fields.text('Temdeglel'),
        'draft_id': fields.many2one('loan.draft','Zeeliin buteegdehuun'),

    }
     
loan_surety_thirdparty()




class xac_loan(osv.osv):
    _name = "xac.loan"
    _description = "Хас Банкнаас олгох зээлүүд"
    _columns = {
        'name': fields.char('Ner',size=128,required=True),
        'amount_min': fields.float('Zeeliin hamgiin baga hemjee',required=True),
        'amount_max': fields.float('Zeeliin hamgiin ih hemjee',required=True),
        'date_min': fields.integer('Zeeliin hamgiin bogino hugatsaa(Saraar)',required=True),
        'date_max': fields.integer('Zeeliin hamgiin ih hugatsaa (Saraar)',required=True),
        'rate_min': fields.float('Huugiin dood hemjee (%)', required=True),
        'rate_max': fields.float('Huugiin deed hemjee (%)', required=True),
        'note': fields.text(u'Tailbar'),
        'active': fields.boolean(u'Idevhitei'),
        'type': fields.selection([('for_own',u'Хувийн болон өрхийн хэрэглээнд'),('for_bussines',u'Бизнест')],'Zeeliin torol',required=True),
        'partners': fields.many2many('xac.partner','xacloan_partnerloan_rel','loan_id','partner_id',u'Zeeldegchid'),
        'requirements': fields.many2many('loan.requirements','loan_requirements_rel','loan_id','requirement_id','Bichig barimtiin burduulber'),
    }
    
    _defaults = {
        'type': lambda *a: 'for_own'
    }
xac_loan()

class loan_direction(osv.osv):
    _name = "loan.direction"
    _description = "Зээлийн зорилго"
    _columns = {
        'name': fields.char('Ner',size=128,required=True),
        'note': fields.text('Tailbar'),
        'type': fields.selection([('for_own','Хувийн болон өрхийн хэрэгцээнд'),('for_business','Бизнест')],'Torol',required=True),
        'active': fields.boolean('Idevhitei'),
    }
    _defaults = {
        'type': lambda *a: 'for_own'
    }
loan_direction()




class loan_order(osv.osv):
    _name = "loan.order"
    _description = "Зээлийн өргөдөл"
    _columns = {
        'partner_id': fields.many2one('xac.partner','Hariltsagch',readonly=True),
        'loan_id': fields.many2one('xac.loan','Zeeliin torol',required=True),
        'note': fields.text('Busad temdeglel'),
        'date': fields.datetime('Ognoo',readonly=True),
        'requirements': fields.one2many('loan.requirements.log','order_id','Bichig barimtiin burduulber'),
        'services': fields.one2many('xac.service.log','order_id','Sanal bolgoh busad buteegdehuun,uilchilgee')
    }
    def _get_partners(self,cr,uid,context={}):
        if context.get('partner_id',False):
            return context['partner_id']
        return False
    
    _defaults = {
        'partner_id': _get_partners,
        'date': lambda *a: time.strftime("%Y-%m-%d %H:%M:%S"),
    }
loan_order() 

