# -*- coding: utf-8 -*-
##############################################################################
#
#    Tech-Receptives Solutions Pvt. Ltd.
#    Copyright (C)2004-TODAY Tech Receptives(<https://www.techreceptives.com>)
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
from openerp.addons.web import http
from openerp.addons.web.http import request
from openerp.tools.translate import _
from openerp.addons.web.controllers.main import Home 


class CaptchaHome(Home):
    
    @http.route('/web/login', type='http', auth="none")
    def web_login(self, redirect=None, **kw):
        qcontext = self.get_auth_signup_qcontext()
        qcontext['error'] = _("Wrong Captcha !!!")
        #if kw.has_key('g-recaptcha-response') and not request.website.is_captcha_valid(kw['g-recaptcha-response']):
        #    return request.render('web.login', qcontext)
        return super(CaptchaHome,self).web_login(redirect, **kw)
    
    
                
    
