#!/usr/bin/env python
# -*- coding: utf-8 -*-
#################################################################################
#
#    Copyright (c) 2015-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
#
#################################################################################

import xmlrpclib
from openerp import api, fields, models, _
from openerp.exceptions import UserError
from mob import XMLRPC_API

class WkSkeleton(models.Model):
	_inherit= 'wk.skeleton'

	@api.model
	def turn_odoo_connection_off(self):
		""" To be inherited by bridge module for making connection Inactive on Odoo End"""
		res = super(WkSkeleton, self).turn_odoo_connection_off()
		active_obj = self.env['magento.configure'].search([('active','=',True)])
		if active_obj:
			if active_obj[0].state == 'enable':
				active_obj[0].state = 'disable'
		return res

	@api.model
	def turn_odoo_connection_on(self):
		""" To be inherited by bridge module for making connection Active on Odoo End"""
		res = super(WkSkeleton, self).turn_odoo_connection_on()
		active_obj = self.env['magento.configure'].search([('active','=',True)])
		if active_obj:
			active_obj[0].state = 'enable'
		return res

	@api.model
	def set_extra_values(self):
		""" Add extra values"""
		res = super(WkSkeleton, self).set_extra_values()
		ctx = dict(self._context or {})
		if ctx.has_key('picking_id') and ctx.has_key('carrier_tracking_ref') and ctx.has_key('carrier_code') and ctx.has_key('mage_ship_number'): 
			picking_obj = self.env['stock.picking'].browse(ctx['picking_id'])
			picking_obj.write({
								'carrier_tracking_ref':ctx['carrier_tracking_ref'],
								'carrier_code':ctx['carrier_code'],
								'magento_shipment':ctx['mage_ship_number']
							})
		return res

	@api.model
	def get_magento_configuration_data(self):

		ir_values_obj = self.env['ir.values']
		mob_sales_team = ir_values_obj.get_default('crm.team', 'mob_sales_team')
		mob_sales_person = ir_values_obj.get_default('res.users', 'mob_sales_person')
		mob_payment_term = ir_values_obj.get_default('account.payment.term', 'mob_payment_term')
		
		return {'team_id':mob_sales_team,	'user_id':mob_sales_person,	'payment_term_id':mob_payment_term}

	@api.model
	def create_sale_order_line(self, data):
		if data.has_key('tax_id'):
			taxes = data.get('tax_id')
			if type(taxes) != list:
				taxes = [data.get('tax_id')]
			data['tax_id'] = [(6,0,taxes)]
		else:
			data['tax_id'] = False
		return super(WkSkeleton, self).create_sale_order_line(data)
		
	@api.model
	def get_magento_virtual_product_id(self, data):
		erp_product_id = False
		ir_values = self.env['ir.values']
		if data['name'].startswith('S'):
			carrier_obj = self.env['sale.order'].browse(data['order_id']).carrier_id
			erp_product_id = carrier_obj.product_id.id
		if data['name'].startswith('D'):
			erp_product_id = ir_values.get_default('product.product', 'mob_discount_product')
		if data['name'].startswith('V'):
			erp_product_id = ir_values.get_default('product.product', 'mob_coupon_product')
		if not erp_product_id:
			temp_dic={'sale_ok':False, 'name':data.get('name'), 'type':'service', 'list_price':0.0}
			object_name = ''
			if data['name'].startswith('D'):
				object_name = 'mob_discount_product'
				temp_dic['description']='Service Type product used by Magento Odoo Bridge for Discount Purposes'
			if data['name'].startswith('V'):
				object_name = 'mob_coupon_product'
				temp_dic['description']='Service Type product used by Magento Odoo Bridge for Gift Voucher Purposes'
			erp_product_id = self.env['product.product'].create(temp_dic).id
			ir_values.set_default('product.product', object_name, erp_product_id)
			self._cr.commit()		
		return erp_product_id

	@api.model
	def create_order_mapping(self, map_data):
		map_data['instance_id'] = self._context['instance_id']
		return super(WkSkeleton, self).create_order_mapping(map_data)
	
class WkOrderMapping(models.Model):			
	_inherit="wk.order.mapping"

	instance_id = fields.Many2one('magento.configure',string='Magento Instance')