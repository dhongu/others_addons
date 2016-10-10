#!/usr/bin/env python
# -*- coding: utf-8 -*-
#################################################################################
#
#    Copyright (c) 2015-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
#
#################################################################################

from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp import workflow

def _unescape(text):
	from urllib import unquote_plus
	return unquote_plus(text.encode('utf8'))

class wk_skeleton(osv.osv):
	_name = "wk.skeleton"
	_description = " Skeleton for all XML RPC imports in Odoo"

	def turn_odoo_connection_off(self, cr, uid, context=None):
		""" To be inherited by bridge module for making connection Inactive on Odoo End"""
		return True

	def turn_odoo_connection_on(self, cr, uid, context=None):
		""" To be inherited by bridge module for making connection Active on Odoo End"""
		return True

	def set_extra_values(self, cr, uid, context=None):
		""" Add extra values"""				
		return True
	# Order Status Updates

	def set_order_cancel(self, cr, uid, order_id, context=None):
		"""Cancel the order in Odoo via requests from XML-RPC  
			@param order_id: Odoo Order ID
			@param context: Mandatory Dictionary with key 'ecommerce' to identify the request from E-Commerce
			@return: A dictionary of status and status message of transaction"""
		context = context or {}
		status = True
		status_message = "Order Successfully Cancelled."
		try:
			pick_obj = self.pool.get('stock.picking')
			sale = self.pool.get('sale.order').browse(cr, uid, order_id)
			if sale.invoice_ids:
				for invoice in sale.invoice_ids:
					self.pool.get('account.journal').write(cr, uid, invoice.journal_id.id,{'update_posted':True})
					if invoice.state == "paid":
						for payment in invoice.payment_ids:
							voucher_ids = self.pool.get('account.voucher').search(cr, uid,[('move_ids.name','=',payment.name)])
							if voucher_ids:
								for voucher in self.pool.get('account.voucher').browse(cr, uid, voucher_ids):
									self.pool.get('account.journal').write(cr, uid, voucher.journal_id.id,{'update_posted':True})
									self.pool.get('account.voucher').cancel_voucher(cr, uid, voucher.journal_id.id, context=context)
					self.pool.get('account.invoice').action_cancel(cr, uid, [invoice.id], context)
			if sale.picking_ids:
				for picking in sale.picking_ids:
					if picking.state == "done":
						status = False
						status_message = 'Cannot cancel a Shipped Order!!!'
						break
					pick_obj.action_cancel(cr, uid, [picking.id], context)
			self.pool.get('sale.order').action_cancel(cr, uid, [order_id], context)
		except Exception, e:
			status = False
			status_message = "Error in Cancelling Order: "%str(e)
		finally:
			return {
				'status_message': status_message,
				'status': status
			}

	def set_order_shipped(self, cr, uid, order_id, context=None):
		"""Cancel the order in Odoo via requests from XML-RPC  
		@param order_id: Odoo Order ID
		@param context: Mandatory Dictionary with key 'ecommerce' to identify the request from E-Commerce
		@return:  A dictionary of status and status message of transaction"""
		context = context or {}
		status = True
		status_message = "Order Successfully Shipped."
		try:
			sale_pool = self.pool.get('sale.order')
			sale = sale_pool.browse(cr, uid, order_id)
			if sale.state == 'draft':
				self.confirm_odoo_order(cr, uid, [order_id], context)
			if sale.picking_ids:
				self.turn_odoo_connection_off(cr, uid, context)
				for picking in sale.picking_ids:
					if picking.state != 'done':
						self.pool.get('stock.picking').do_transfer(cr, uid, picking.id, context)
						context['picking_id'] = picking.id
						self.set_extra_values(cr, uid, context)
				self.turn_odoo_connection_on(cr, uid, context)
		except Exception,e:
			status = False
			status_message = "Error in Delivering Order: "%str(e)
		finally:
			return {
				'status_message': status_message,
				'status': status
			}

	def set_order_paid(self, cr, uid, payment_data, context=None):
		"""Make the order Paid in Odoo via requests from XML-RPC  
		@param payment_data: A standard dictionary consisting of 'order_id', 'journal_id', 'amount'
		@param context: A Dictionary with key 'ecommerce' to identify the request from E-Commerce
		@return:  A dictionary of status and status message of transaction"""
		context = context or {}
		status = True
		counter = 0
		draft_invoice_ids = []
		invoice_id = False
		status_message = "Payment Successfully made for Order."
		try:
			journal_id = payment_data.get('journal_id',False)
			sale_obj = self.pool.get('sale.order').browse(cr, uid, payment_data['order_id'])
			if not sale_obj.invoice_ids:
				create_invoice = self.create_order_invoice(cr, uid, payment_data['order_id'], context=context)
				if create_invoice['status']:
					draft_invoice_ids.append(create_invoice['invoice_id'])
					draft_amount = self.pool.get('account.invoice').browse(cr, uid, create_invoice['invoice_id']).amount_total
			elif sale_obj.invoice_ids:
				# currently supporting only one invoice per sale order to be paid
				for invoice in sale_obj.invoice_ids:
					if invoice.state == 'open':
						invoice_id = invoice.id
					elif invoice.state == 'draft':
						draft_invoice_ids.append(invoice.id)
					counter+=1
			if counter <=1:
				if draft_invoice_ids:
					workflow.trg_validate(uid, 'account.invoice', draft_invoice_ids[0], 'invoice_open', cr)
					invoice_id = draft_invoice_ids[0]
				#Setting Context for Payment Wizard
				ctx = {'default_invoice_ids': [[4, invoice_id, None]], 'active_model': 'account.invoice', 'journal_type': 'sale', 'search_disable_custom_filters': True, 'active_ids': [invoice_id], 'type': 'out_invoice', 'active_id': invoice_id}
				context.update(ctx)
				#Getting all default field values for Payment Wizard
				fields = ['communication', 'currency_id', 'invoice_ids', 'payment_difference', 'partner_id', 'payment_method_id', 'payment_difference_handling', 'journal_id', 'state', 'writeoff_account_id', 'payment_date', 'partner_type', 'hide_payment_method', 'payment_method_code', 'amount', 'payment_type']
				default_vals = self.pool.get('account.payment').default_get(cr, uid, fields, context)
				payment_method_id = self.get_default_payment_method(cr, uid, journal_id, context)
				default_vals.update({'journal_id':journal_id, 'payment_method_id':payment_method_id})
				payment = self.pool.get('account.payment').create(cr, uid, default_vals, context)
				paid = self.pool.get('account.payment').browse(cr, uid, payment).post()
			else:
				status = False
				status_message = "Multiple validated Invoices found for the Odoo order. Cannot make Payment"
		except Exception, e:
			status_message = "Error in creating Payments for Invoice: "%str(e)
			status = False
		finally:
			return {
				'status_message': status_message,
				'status': status
			}

	def get_default_payment_method(self, cr, uid, journal_id, context=None):
		""" @params journal_id: Journal Id for making payment
			@params context : Must have key 'ecommerce' and then return payment payment method based on Odoo Bridge used else return the default payment method for Journal
			@return: Payment method ID(integer)"""				
		payment_method_ids = self.pool.get('account.journal').browse(cr, uid, journal_id)._default_inbound_payment_methods()
		if payment_method_ids:
			return payment_method_ids[0].id
		return False

	def get_default_configuration_data(self, cr, uid, ecommerce_channel, context=None):
		"""@return: Return a dictionary of Sale Order keys by browsing the Configuration of Bridge Module Installed"""
		if hasattr(self,'get_%s_configuration_data'%ecommerce_channel):
			return getattr(self,'get_%s_configuration_data'%ecommerce_channel)(cr, uid, context)
		else:
			return False

	def create_order_mapping(self, cr, uid, map_data, context=None):
		"""Create Mapping on Odoo end for newly created order
		@param order_id: Odoo Order ID
		@context : A dictionary consisting of e-commerce Order ID"""
		
		self.pool.get('wk.order.mapping').create(cr, uid, map_data)
		return True

	def create_order(self, cr, uid, sale_data, context=None):
		""" Create Order on Odoo along with creating Mapping
		@param sale_data: dictionary of Odoo sale.order model fields
		@param context: Standard dictionary with 'ecommerce' key to identify the origin of request and
						e-commerce order ID.	
		@return: A dictionary with status, order_id, and status_message"""
		context = context or {}
		# check sale_data for min no of keys presen or not
		order_name,order_id,status,status_message = "",False, True, "Order Successfully Created."
		config_data = self.get_default_configuration_data(cr, uid, sale_data['ecommerce_channel'], context)
		sale_data.update(config_data)

		try:
			order_id = self.pool.get('sale.order').create(cr, uid, sale_data, context=context)
			order_name = self.pool.get('sale.order').read(cr, uid, order_id, ['name'], context=context)['name']
			self.create_order_mapping(cr, uid, {
				'ecommerce_channel':sale_data['ecommerce_channel'],
				'erp_order_id':order_id,
				'ecommerce_order_id':sale_data['ecommerce_order_id'],
				'name':sale_data['origin'],
				}, context=context)
		except Exception, e:
			status_message = "Error in creating order on Odoo: %s"%str(e)
			status = False
		finally:
			return {
				'order_id': order_id,
				'order_name': order_name,
				'status_message': status_message,
				'status': status
			}

	def create_sale_order_line(self, cr, uid, order_line_data, context=None):
		"""Create Sale Order Lines from XML-RPC
		@param order_line_data: A dictionary of Sale Order line fields in which required field(s) are 'order_id', `product_uom_qty`, `price_unit`
			`product_id`: mandatory for non shipping/voucher order lines
		@return: A dictionary of Status, Order Line ID, Status Message  """
		context = context or {}
		status = True
		order_line_id = False
		status_message = "Order Line Successfully Created."
		try:
			# To FIX:
			# Cannot call Onchange in sale order line
			product_obj = self.pool.get('product.product').browse(cr, uid, order_line_data['product_id'])
			order_line_data.update({'product_uom':product_obj.uom_id.id})
			if order_line_data.has_key('name'):
				order_line_data['name'] = _unescape(order_line_data['name'])
			else:
				order_line_data.update({'name':product_obj.description_sale or product_obj.name})
			order_line_id = self.pool.get('sale.order.line').create(cr, uid, order_line_data, context=context)
		except Exception, e:
			status_message = "Error in creating order Line on Odoo: "%str(e)
			status = False
		finally:
			return {
				'order_line_id':order_line_id,
				'status': status,
				'status_message': status_message
			}

	def create_order_shipping_and_voucher_line(self, cr, uid, order_line, context=None):
		""" @params order_line: A dictionary of sale ordre line fields
			@params context: a standard odoo Dictionary with context having keyword to check origin of fumction call and identify type of line for shipping and vaoucher
			@return : A dictionary with updated values of order line"""
		product_id = self.get_default_virtual_product_id(cr, uid, order_line, context=context)
		order_line['product_id'] = product_id
		res = self.create_sale_order_line(cr, uid, order_line, context=context)		
		return res

	def get_default_virtual_product_id(self, cr, uid, order_line, context=None):
		ecommerce_channel = order_line['ecommerce_channel']
		if hasattr(self,'get_%s_virtual_product_id'%ecommerce_channel):
			return getattr(self,'get_%s_virtual_product_id'%ecommerce_channel)(cr, uid, order_line, context)
		else:
			return False
		
	def confirm_odoo_order(self, cr, uid, order_id, context=None):
		""" Confirms Odoo Order from E-Commerce
		@param order_id: Odoo/ERP Sale Order ID
		@return: a dictionary of True or False based on Transaction Result with status_message"""
		if isinstance(order_id, (int, long)):
			order_id = [order_id]
		context = context or {}
		status = True
		status_message = "Order Successfully Confirmed!!!"
		try:
			self.pool.get('sale.order').action_confirm(cr, uid, order_id)
		except Exception, e:
			status_message = "Error in Confirming Order on Odoo: "%str(e)
			status = False
		finally:
			return {
				'status': status,
				'status_message': status_message
			}

	def create_order_invoice(self, cr, uid, order_id, context=None):
		"""Creates Order Invoice by request from XML-RPC.
		@param order_id: Odoo Order ID
		@return: a dictionary containig Odoo Invoice IDs and Status with Status Message
		"""
		context = context or {}
		invoice_id = False
		status = True
		status_message = "Invoice Successfully Created."
		try:
			sale_obj = self.pool.get('sale.order').browse(cr, uid, order_id, context)
			invoice_id = sale_obj.invoice_ids
			if sale_obj.state == 'draft':
				self.confirm_odoo_order(cr, uid, order_id, context)
			if not invoice_id:
				invoice_id = self.pool.get('sale.order').action_invoice_create(cr, uid, order_id)
			else:
				status = False
				status_message = "Invoice Already Created"
		except Exception, e:
			status = False
			status_message = "Error in creating Invoice: "%str(e)
		finally:
			return {
				'status': status,
				'status_message': status_message,
				'invoice_id': invoice_id[0]
			}

ORDER_STATUS = [
		('draft', 'Quotation'),
		('sent', 'Quotation Sent'),
		('cancel', 'Cancelled'),
		('sale', 'Sales Order'),
		('done', 'Done'),
]

############## Mapping classes #################
class wk_order_mapping(osv.osv):
	_name="wk.order.mapping"
	_columns = {
		'name': fields.char('eCommerce Order Ref.',size=100),
		'ecommerce_channel':fields.related('erp_order_id', 'ecommerce_channel', type="char", string="eCommerce Channel"),	
		'erp_order_id':fields.many2one('sale.order', 'ODOO Order Id',required=1),	
		'ecommerce_order_id':fields.integer('eCommerce Order Id',required=1),
		'order_status': fields.related('erp_order_id', 'state', type='selection', selection=ORDER_STATUS, string='Order Status'),
		'is_invoiced': fields.related('erp_order_id', 'is_invoiced', type='boolean', relation='sale.order', string='Paid'),
		'is_shipped': fields.related('erp_order_id', 'is_shipped', type='boolean', relation='sale.order', string='Shipped'),
	}
wk_order_mapping()