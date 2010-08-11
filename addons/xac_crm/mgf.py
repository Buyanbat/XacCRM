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

class partner_other_relations(osv.osv):
    _name = "partner.other.relations"
    _description = "Харилцагчийн бусад банк, санхүүгийн байгууллагаас авдаг үйлчилгээ"
    _columns = {
        'name': fields.char("Банкны нэр",size=128),
        'mgf_id': fields.many2one('partner.mgf','MGF'),
        'account':fields.char('Эзэмшдэг данс',size=128),
        'balance':fields.float('Үлдэгдэл'),
        'interest': fields.float('Хүү(%)'),
        'method': fields.char('Үлдэгдлээ хэрхэн хянадаг вэ?',size=256),
    }
partner_other_relations()

class partner_previous_loans(osv.osv):
    _name = "partner.previous.loans"
    _description = "Харилцагчийн өмнө нь авч байсан зээлийн мэдээлэл"
    _columns = {
        'name': fields.char('Зээлдүүлэгч',size=128),
        'surety': fields.char('Барьцаа',size=128),
        'amount': fields.float('Үлдэгдэл'),
        'real_amount': fields.float('Зах зээлийн үлдэгдэл'),
        'interest': fields.float('Хүү (%)'),
                
    }
partner_previous_loans()        

class partner_mgf(osv.osv):
    _name = "partner.mgf"
    _description = "Харилцагчийн MGF"
    _columns = {
        'partner_id': fields.many2one('xac.partner','Харилцагч'),
    }

partner_mgf()