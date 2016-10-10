# -*- coding: utf-8 -*-
#################################################################################
#
#    Copyright (c) 2015-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
#
#################################################################################


import xmlrpclib
from openerp import api, fields, models, _
from openerp.exceptions import UserError

from openerp.addons.magento_bridge.models.mob import XMLRPC_API

################## .............magento-Odoo stock.............##################

class StockMove(models.Model):
	_inherit="stock.move"

	@api.multi
	def action_confirm(self):
		""" Confirms stock move or put it in waiting if it's linked to another move.
		"""
		mob_stock_action = self.env['ir.values'].get_default('mob.config.settings', 'mob_stock_action')
		res = super(StockMove, self).action_confirm()
		if mob_stock_action == "fq":
			self.fetch_stock_warehouse()
		return res

	@api.multi
	def action_cancel(self):
		""" Confirms stock move or put it in waiting if it's linked to another move.
		"""
		ctx = dict(self._context or {})
		ctx['action_cancel'] = True
		mob_stock_action = self.env['ir.values'].get_default('mob.config.settings', 'mob_stock_action')
		check = False
		for obj in self:
			if obj.state == "cancel":
				check = True
		res = super(StockMove, self).action_cancel()
		if mob_stock_action == "fq" and not check:
			self.with_context(ctx).fetch_stock_warehouse()
		return res

	@api.multi
	def action_done(self):
		""" Process completly the moves given as ids and if all moves are done, it will finish the picking.
		"""
		mob_stock_action = self.env['ir.values'].get_default('mob.config.settings', 'mob_stock_action')
		check = False
		for obj in self:
			if obj.location_id.name == "Inventory loss" or obj.location_dest_id.name == "Inventory loss":
				check = True
		res = super(StockMove, self).action_done()
		if mob_stock_action == "qoh" or check:
			self.fetch_stock_warehouse()
		return res

	@api.multi
	def fetch_stock_warehouse(self):
		if not self._context.has_key('stock_from'):
			for data in self:
				erp_product_id = data.product_id.id
				flag = 1
				if data.origin and data.origin.startswith('SO'):
					sale_obj = data.env['sale.order'].search([('name','=',data.origin)])
					if sale_obj:
						get_channel = sale_obj[0].ecommerce_channel
						if get_channel == 'magento':
							flag=0
				else:
					flag = 2 # no origin
				product_qty = 0
				warehouse_id = 0
				if flag == 1:
					product_qty = int(data.product_qty)
					if 'OUT' in data.picking_id.name and not data._context.has_key('action_cancel'):
						product_qty = int(-product_qty)
					if 'IN' in data.picking_id.name and data._context.has_key('action_cancel'):
						product_qty = int(-product_qty)
					warehouse_id = data.warehouse_id.id
				if flag == 2:
					location_id = data.location_dest_id.id
					company_id = data.company_id.id
					check_in1 = self.env['stock.warehouse'].search([('lot_stock_id','=',location_id),('company_id','=',company_id)],limit=1)
					check_in = self.env['stock.warehouse'].search([('lot_stock_id','=',location_id),('company_id','=',company_id)])					
					if not check_in:
						check_in = data.check_warehouse_location(data.location_dest_id, data.company_id.id)
					if check_in[0]:
						# Getting Goods.
						warehouse_id = check_in[0].id
						if data._context.has_key('action_cancel'):
							product_qty = int(-data.product_qty)
						else:
							product_qty = int(data.product_qty)
					check_out = self.env['stock.warehouse'].search([('lot_stock_id','=',data.location_id.id),('company_id','=',data.company_id.id)],limit=1)
					if not check_out:
						check_out = data.check_warehouse_location(data.location_id, data.company_id.id)
					if check_out[0]:
						# Sending Goods.
						warehouse_id = check_out[0].id
						if data._context.has_key('action_cancel'):
							product_qty = int(data.product_qty)
						else:
							product_qty = int(-data.product_qty)
				data.check_warehouse(erp_product_id, warehouse_id, product_qty)
		return True

	@api.one
	def check_warehouse_location(self, location_obj, company_id):
		flag = True
		check_in = []
		while flag == True and location_obj:
			location_obj = location_obj.location_id
			check_in = self.env['stock.warehouse'].search([('lot_stock_id','=',location_obj.id),('company_id','=',company_id)],limit=1)
			if check_in:
				flag = False
		return check_in

	@api.one
	def check_warehouse(self, erp_product_id, warehouse_id, product_qty):
		mapping_ids = self.env['magento.product'].search([('pro_name','=',erp_product_id)])
		if mapping_ids:
			mapping_obj = mapping_ids[0]
			instance_obj = mapping_obj.instance_id
			mage_product_id = mapping_obj.mag_product_id
			if mapping_obj.instance_id.warehouse_id.id == warehouse_id:
				self.synch_quantity(mage_product_id, product_qty, instance_obj)
			
	@api.one
	def synch_quantity(self, mage_product_id, product_qty, instance_obj):
		response = self.update_quantity(mage_product_id, product_qty, instance_obj)
		if response[0][0]==1:
			return True
		else:
			self.env['magento.sync.history'].create({'status':'no','action_on':'product','action':'c','error_message':response[0][1]})
		
	@api.one
	def update_quantity(self, mage_product_id, quantity, instance_obj):
		qty = 0
		text = ''
		stock = 0
		session = False
		ctx = dict(self._context or {})
		ctx['instance_id'] = instance_obj.id
		if mage_product_id:
			if not instance_obj.active :
				return [0,' Connection needs one Active Configuration setting.']
			else:
				url = instance_obj.name + XMLRPC_API
				user = instance_obj.user
				pwd = instance_obj.pwd
				try:
					server = xmlrpclib.Server(url)
					session = server.login(user,pwd)
				except xmlrpclib.Fault, e:
					text = 'Error, %s Magento details are Invalid.'%e
				except IOError, e:
					text = 'Error, %s.'%e
				except Exception,e:
					text = 'Error in Magento Connection.'
				if not session:
					return [0,text]
				else:
					try:
						if type(quantity)==str:
							quantity = quantity.split('.')[0]
						if type(quantity)==float:
							quantity = quantity.as_integer_ratio()[0]
						stock_search = server.call(session, 'magerpsync.update_product_stock', [[mage_product_id, quantity]])
						return [1, '']
					except Exception,e:
						return [0,' Error in Updating Quantity for Magneto Product Id %s'%mage_product_id]
		else:
			return [1, 'Error in Updating Stock, Magento Product Id Not Found!!!']