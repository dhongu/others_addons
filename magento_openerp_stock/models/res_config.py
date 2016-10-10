# -*- coding: utf-8 -*-
#################################################################################
#
#    Copyright (c) 2015-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
#
#################################################################################

from openerp import api, fields, models, _
from openerp.exceptions import UserError

class MobConfigSettings(models.TransientModel):
    _inherit = 'mob.config.settings'


    mob_stock_action = fields.Selection([('qoh', 'Quantity on hand'),('fq', 'Forecast Quantity')], string='Stock Management',help="Manage Stock")

    @api.multi
    def set_default_stock_fields(self):
        self.env['ir.values'].set_default('mob.config.settings', 'mob_stock_action', self.mob_stock_action or False)
        return True
    
    @api.multi
    def get_default_stock_fields(self):
        mob_stock_action = self.env['ir.values'].get_default('mob.config.settings', 'mob_stock_action')
        return {'mob_stock_action':mob_stock_action}