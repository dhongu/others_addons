# -*- coding: utf-8 -*-
#################################################################################
#
#    Copyright (c) 2015-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
#
#################################################################################


import openerp
from openerp import SUPERUSER_ID
from openerp import api, fields, models, _
from openerp.exceptions import UserError

class MobConfigSettings(models.TransientModel):
    _name = 'mob.config.settings'
    _inherit = 'res.config.settings'

    mob_discount_product = fields.Many2one('product.product', string="Discount Product",
            help="""Service type product used for Discount purposes.""")
    mob_coupon_product = fields.Many2one('product.product', string="Coupon Product",
            help="""Service type product used in Coupon.""")
    mob_payment_term = fields.Many2one('account.payment.term', string="Magento Payment Term",
            help="""Default Payment Term Used In Sale Order.""")
    mob_sales_team = fields.Many2one('crm.team', string="Magento Sales Team",
            help="""Default Sales Team Used In Sale Order.""")
    mob_sales_person = fields.Many2one('res.users', string="Magento Sales Person",
            help="""Default Sales Person Used In Sale Order.""")
    mob_sale_order_invoice = fields.Boolean(string="Invoice")
    mob_sale_order_shipment = fields.Boolean(string="Shipping")
    mob_sale_order_cancel = fields.Boolean(string="Cancel")

    @api.multi
    def set_default_fields(self):
        ir_values_obj = self.env['ir.values']
        ir_values_obj.sudo().set_default('product.product', 'mob_discount_product',
            self.mob_discount_product and self.mob_discount_product.id or False)
        ir_values_obj.sudo().set_default('product.product', 'mob_coupon_product',
            self.mob_coupon_product and self.mob_coupon_product.id or False)
        ir_values_obj.sudo().set_default('account.payment.term', 'mob_payment_term',
            self.mob_payment_term and self.mob_payment_term.id or False)
        ir_values_obj.sudo().set_default('crm.team', 'mob_sales_team',
            self.mob_sales_team and self.mob_sales_team.id or False)
        ir_values_obj.sudo().set_default('res.users', 'mob_sales_person',
            self.mob_sales_person and self.mob_sales_person.id or False)
        ir_values_obj.sudo().set_default('mob.config.settings', 'mob_sale_order_shipment', self.mob_sale_order_shipment or False)
        ir_values_obj.sudo().set_default('mob.config.settings', 'mob_sale_order_cancel', self.mob_sale_order_cancel or False)
        ir_values_obj.sudo().set_default('mob.config.settings', 'mob_sale_order_invoice', self.mob_sale_order_invoice or False)
        return True
    
    @api.multi
    def get_default_fields(self):
        ir_values_obj = self.env['ir.values']
        mob_discount_product = ir_values_obj.sudo().get_default('product.product', 'mob_discount_product')
        mob_coupon_product = ir_values_obj.sudo().get_default('product.product', 'mob_coupon_product')
        mob_payment_term = ir_values_obj.sudo().get_default('account.payment.term', 'mob_payment_term')
        mob_sales_team = ir_values_obj.sudo().get_default('crm.team', 'mob_sales_team')
        mob_sales_person = ir_values_obj.sudo().get_default('res.users', 'mob_sales_person')
        mob_sale_order_shipment = ir_values_obj.sudo().get_default('mob.config.settings', 'mob_sale_order_shipment')
        mob_sale_order_cancel = ir_values_obj.sudo().get_default('mob.config.settings', 'mob_sale_order_cancel')
        mob_sale_order_invoice = ir_values_obj.sudo().get_default('mob.config.settings', 'mob_sale_order_invoice')
        return {
                'mob_discount_product':mob_discount_product,
                'mob_coupon_product':mob_coupon_product,
                'mob_payment_term':mob_payment_term,
                'mob_sales_team':mob_sales_team,
                'mob_sales_person':mob_sales_person,
                'mob_sale_order_shipment':mob_sale_order_shipment,
                'mob_sale_order_invoice':mob_sale_order_invoice,
                'mob_sale_order_cancel':mob_sale_order_cancel,
                }
