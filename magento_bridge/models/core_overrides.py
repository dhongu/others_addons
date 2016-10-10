# -*- coding: utf-8 -*-
#################################################################################
#
#    Copyright (c) 2015-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
#
#################################################################################

import re
import openerp
from mob import _unescape
from mob import XMLRPC_API
import xmlrpclib
from openerp import api, fields, models, _
from openerp.exceptions import UserError

class ProductAttribute(models.Model):
	_inherit= 'product.attribute'

	@api.multi
	def _check_unique_insesitive(self):
		sr_ids = self.search([])
		if sr_ids:
			lst = [x.name.lower() for x in sr_ids if x.name and x.id not in self.ids]
			for self_obj in self:
				if self_obj.name and self_obj.name.lower() in  lst:
					return False
				return True
		return False
	
	@api.multi
	def _check_valid_attribute(self):
		check_valid = re.search(r"^[a-z][a-z_0-9]{1,30}$", self.name)
		if check_valid:
			return True
		else:
			return False
	_constraints = [(_check_unique_insesitive, 'Attribute name already exists', ['name']),
	(_check_valid_attribute, 'Must be unique and in lowercase with no spaces. Maximum length of attribute code must be less then 30 symbols', ['name'])
	]

	@api.model
	def check_attribute(self, vals):
		attribute_ids = self.search([])		
		for attribute_obj in attribute_ids:
			if attribute_obj.name.lower() == vals['name']:
				return attribute_obj
		return False

	@api.model
	def create(self, vals):
		attribute_obj = self.check_attribute(vals)
		if attribute_obj and self._context.has_key('magento'):			
			return attribute_obj
		else:
			return super(ProductAttribute, self).create(vals)

class ProductAttributeValue(models.Model):
	_inherit= 'product.attribute.value'

	@api.model
	def create(self, vals):
		attribute_value_ids = self.search([('name','=',vals.get('name')),('attribute_id','=',vals.get('attribute_id'))])
		if attribute_value_ids and self._context.has_key('magento'):
			return attribute_value_ids[0]
		else:
			return super(ProductAttributeValue, self).create(vals)

class ProductTemplate(models.Model):
	_inherit = "product.template"

	@api.model
	def _inactive_default_variant(self, product_template_obj):
		varinat_ids = product_template_obj.product_variant_ids
		for vid in varinat_ids:
			att_line_ids = vid.attribute_line_ids
			if not att_line_ids:
				vid.active = False
		return True

	prod_type = fields.Char(string='Magento Type')
	categ_ids = fields.Many2many('product.category','product_categ_rel','product_id','categ_id', string='Product Categories')
	attribute_set_id = fields.Many2one('magento.attribute.set', string='Magento Attribute Set', help="Magento Attribute Set, Used during configurable product generation at Magento.")

	@api.model
	def create(self, vals):
		mage_id = 0
		if self._context.has_key('magento'):
			if vals.has_key('name'):
				vals['name'] = _unescape(vals['name'])
			if vals.has_key('description'):
				vals['description'] = _unescape(vals['description'])
			if vals.has_key('description_sale'):
				vals['description_sale'] = _unescape(vals['description_sale'])
			if vals.has_key('category_ids') and vals.get('category_ids'):
				categ_ids = list(set(vals.get('category_ids')))
				vals['categ_id'] = max(categ_ids)
				categ_ids.remove(max(categ_ids))
				vals['categ_ids'] = [(6, 0, categ_ids)]
				vals.pop('category_ids')
			if vals.has_key('mage_id'):
				mage_id = vals.get('mage_id')
				vals.pop('mage_id')
		product_template_obj = super(ProductTemplate, self).create(vals)
		if self._context.has_key('magento') and self._context.has_key('configurable'):
			mapping_data = {
							'template_name':product_template_obj.id,
							'erp_template_id':product_template_obj.id,
							'mage_product_id':mage_id,
							'base_price':vals['list_price'],
							'is_variants':True,
							'instance_id':self._context.get('instance_id'),
							'created_by':'Magento'
						}
			self.env['magento.product.template'].create(mapping_data)
			self._inactive_default_variant(product_template_obj)
		return product_template_obj

	@api.multi	
	def write(self, vals):
		if self._context.has_key('magento'):
			if vals.has_key('name'):
				vals['name'] = _unescape(vals['name'])
			if vals.has_key('description'):
				vals['description'] = _unescape(vals['description'])
			if vals.has_key('description_sale'):
				vals['description_sale'] = _unescape(vals['description_sale'])
			if vals.has_key('category_ids') and vals.get('category_ids'):
				categ_ids = list(set(vals.get('category_ids')))
				vals['categ_id'] = max(categ_ids)
				categ_ids.remove(max(categ_ids))
				vals['categ_ids'] = [(6, 0, categ_ids)]
			if vals.has_key('mage_id'):
				vals.pop('mage_id')

		for temp_obj in self:
			temp_map_ids = self.env['magento.product.template'].search([('template_name', '=', temp_obj.id)])
			if temp_map_ids:
				if self._context.has_key('magento'):
					for temp_map_obj in temp_map_ids:
						temp_map_obj.need_sync = 'No'
				else:
					for temp_map_obj in temp_map_ids:
						temp_map_obj.need_sync = 'Yes'
		return super(ProductTemplate, self).write(vals)

	@api.multi	
	def unlink(self):
		connection_ids = self.env['magento.configure'].search([])
		for template_obj in self:
			for connection_obj in connection_ids:
				ctx = dict(self._context or {})
				ctx['instance_id'] = connection_obj.id
				connection = connection_obj.with_context(ctx)._create_connection()
				product_map_obj = self.env['magento.product.template'].search([('erp_template_id','=',template_obj.id),('instance_id','=',connection_obj.id)])
				if product_map_obj:
					product_map_obj[0].with_context(ctx).unlink()
					for product_id in template_obj.product_variant_ids.ids:
						product_map_id = self.env['magento.product'].with_context(ctx).search([('oe_product_id','=',product_id),('instance_id','=',connection_obj.id)])
						if product_map_id:
							product_map_id[0].with_context(ctx).unlink()
							if connection:
								url = connection[0]
								session = connection[1]
								server = xmlrpclib.Server(url)
								try:
									server.call(session,'magerpsync.product_map_delete', [product_id])
								except Exception, e:
									pass
					if template_obj.prod_type == "configurable":
						if connection:
							url = connection[0]
							session = connection[1]
							server = xmlrpclib.Server(url)
							try:
								server.call(session,'magerpsync.template_map_delete', [template_obj.id])								
							except Exception, e:
								pass

		return super(ProductTemplate, self).unlink()

class ProductProduct(models.Model):
	_inherit= 'product.product'

	@api.model
	def create(self, vals):
		mage_id = 0
		attr_val_ids = []
		if self._context.has_key('magento'):
			if vals.has_key('default_code'):
				vals['default_code'] = _unescape(vals['default_code'])
			if vals.has_key('category_ids') and vals.get('category_ids'):
				categ_ids = list(set(vals.get('category_ids')))
				vals['categ_id'] = max(categ_ids)
				categ_ids.remove(max(categ_ids))
				vals['categ_ids'] = [(6, 0, categ_ids)]
				vals.pop('category_ids')
			if vals.has_key('value_ids'):
				attr_val_ids = vals.get('value_ids')
				vals['attribute_value_ids'] = [(6,0,attr_val_ids)]
			if vals.has_key('mage_id'):
				mage_id = vals.get('mage_id')
				vals.pop('mage_id')
		product_obj = super(ProductProduct, self).create(vals)
		if self._context.has_key('magento'):
			mage_temp_env = self.env['magento.product.template']
			template_id = product_obj.product_tmpl_id.id
			if template_id:
				if attr_val_ids:
					for attr_val_id in attr_val_ids:
						attr_id = self.env['product.attribute.value'].browse(attr_val_id).attribute_id.id
						search_ids = self.env['product.attribute.line'].search([('product_tmpl_id','=',template_id),('attribute_id','=',attr_id)])
						for search_obj in search_ids:
							search_obj.value_ids = [(4, attr_val_id)]
				if mage_id:
					search_ids = mage_temp_env.search([('erp_template_id','=', template_id)])
					if not search_ids:
						price = 0
						if vals.has_key('list_price'):
							price = vals['list_price']
						mage_temp_env.create({
											'template_name':template_id,
											'erp_template_id':template_id,
											'mage_product_id':mage_id,
											'base_price':price,
											'instance_id':self._context.get('instance_id'),
											'created_by':'Magento'
											})
					else:
						for search_obj in search_ids:
							search_obj.need_sync = 'No'
					self.env['magento.product'].create({'pro_name':product_obj.id,'oe_product_id':product_obj.id,'mag_product_id':mage_id,'instance_id':self._context.get('instance_id'),'created_by':'Magento'})
					
		return product_obj

	@api.multi
	def write(self, vals):		
		if self._context.has_key('magento'):
			if vals.has_key('default_code'):
				vals['default_code'] = _unescape(vals['default_code'])
			if vals.has_key('category_ids') and vals.get('category_ids'):
				categ_ids = list(set(vals.get('category_ids')))
				vals['categ_id'] = max(categ_ids)
				categ_ids.remove(max(categ_ids))
				vals['categ_ids'] = [(6, 0, categ_ids)]
				vals.pop('category_ids')
			if vals.has_key('mage_id'):
				vals.pop('mage_id')
		for pro_obj in self:
			map_ids = []
			if self._context.has_key('instance_id'):
				map_ids = self.env['magento.product'].search([('pro_name', '=', pro_obj.id),('instance_id', '=', self._context['instance_id'])])
			for map_obj in map_ids:
				if self._context.has_key('magento'):
					map_obj.need_sync = "No"
				else:
					map_obj.need_sync = "Yes"
			template_id = pro_obj.product_tmpl_id.id
			temp_map_ids = self.env['magento.product.template'].search([('template_name', '=', template_id)])
			for temp_map_obj in temp_map_ids:
				if self._context.has_key('magento'):
					temp_map_obj.need_sync = "No"
				else:
					temp_map_obj.need_sync = "Yes"
		return super(ProductProduct, self).write(vals)

class ProductCategory(models.Model):
	_inherit = 'product.category'

	@api.model
	def create(self, vals):
		category_ids = self.search([('name','=',vals.get('name'))])
		if category_ids and self._context.has_key('magento'):
			return category_ids[0]
		else:
			return super(ProductCategory, self).create(vals)

	@api.multi
	def write(self, vals):
		if self._context.has_key('magento'):
			if vals.has_key('name'):
				vals['name'] = _unescape(vals['name'])
		else:
			for cat_obj in self:
				map_ids = self.env['magento.category'].search([('oe_category_id', '=', cat_obj.id)])
				for map_obj in map_ids:
					map_obj.need_sync = "Yes"
		return super(ProductCategory, self).write(vals)

class ResPartner(models.Model):
	_inherit = 'res.partner'

	@api.model
	def create(self, vals):
		if self._context.has_key('magento'):
			vals = self.customer_array(vals)
		return super(ResPartner, self).create(vals)

	@api.multi
	def write(self, vals):
		if self._context.has_key('magento'):
			vals = self.customer_array(vals)		
		return super(ResPartner, self).write(vals)

	def customer_array(self, data):
		dic = {}
		if data.has_key('country_code'):
			country_ids = self.env['res.country'].search([('code','=',data.get('country_code'))])
			data.pop('country_code')
			if country_ids:
				data['country_id'] = country_ids[0].id
				if data.has_key('region') and data['region']:
					region = _unescape(data.get('region'))
					state_ids = self.env['res.country.state'].search([('name', '=', region)])
					if state_ids:
						data['state_id'] = state_ids[0].id
					else:
						dic['name'] = region
						dic['country_id'] = country_ids[0].id
						dic['code'] = region[:2].upper()
						state_id = self.env['res.country.state'].create(dic)
						data['state_id'] = state_id.id
				data.pop('region')
		if data.has_key('tag') and data["tag"]:
			tag = _unescape(data.get('tag'))
			tag_ids = self.env['res.partner.category'].search([('name','=',tag)], limit=1)
			if not tag_ids:
				tag_id = self.env['res.partner.category'].create({'name':tag})
			else:
				tag_id = tag_ids[0].id
			data['category_id'] = [(6,0,[tag_id])]
			data.pop('tag')
		if data.has_key('wk_company'):
			data['wk_company'] = _unescape(data['wk_company'])
		if data.has_key('name') and data['name']:
			data['name'] = _unescape(data['name'])
		if data.has_key('email') and data['email']:
			data['email'] = _unescape(data['email'])
		if data.has_key('street') and data['street']:
			data['street'] = _unescape(data['street'])
		if data.has_key('street2') and data['street2']:
			data['street2'] = _unescape(data['street2'])
		if data.has_key('city') and data['city']:
			data['city'] = _unescape(data['city'])
		return data

class SaleOrder(models.Model):
	_inherit = "sale.order"

	@api.model
	def _get_ecommerces(self):
		res = super(SaleOrder, self)._get_ecommerces()
		res.append(('magento','Magento'))
		return res

	@api.one
	def action_cancel(self):
		res = super(SaleOrder, self).action_cancel()
		enable_order_cancel = self.env['ir.values'].get_default('mob.config.settings', 'mob_sale_order_cancel')
		if self.ecommerce_channel == "magento" and enable_order_cancel:
			self.manual_magento_order_operation("cancel")
		return res

	@api.one
	def manual_magento_order_operation(self, opr):
		text = ''
		status = 'no'
		session = False
		mage_shipment = False
		mapping_obj = self.env['wk.order.mapping'].search([('erp_order_id','=', self.id)])
		if mapping_obj:
			increment_id = mapping_obj[0].name
			order_name = self.name
			connection_obj = mapping_obj[0].instance_id
			if connection_obj.active:
				obj = connection_obj
				if obj.state != 'enable':
					text = 'Please create the configuration part for connection!!!'
				else:
					url = obj.name + XMLRPC_API
					user = obj.user
					pwd = obj.pwd
					email = obj.notify
					try:
						server = xmlrpclib.Server(url)
						session = server.login(user,pwd)
					except xmlrpclib.Fault, e:
						text = 'Error, %s Magento details are Invalid.'%e
					except IOError, e:
						text = 'Error, %s.'%e
					except Exception,e:
						text = 'Error in Magento Connection.'
					if session and increment_id:
						if opr == "shipment":
							try:							
								mage_shipment = server.call(session,'magerpsync.order_shippment', [increment_id, "Shipped From Odoo", email])
								text = 'shipment of order %s has been successfully updated on magento.'%order_name
								status = 'yes'
							except xmlrpclib.Fault, e:
								text = 'Magento shipment Error For Order %s , Error %s.'%(order_name, e)								
						elif opr == "cancel":
							try:
								server.call(session,'sales_order.cancel',[increment_id])
								text = 'sales order %s has been sucessfully canceled from magento.'%order_name
								status = 'yes'
							except Exception,e:
								text = 'Order %s cannot be canceled from magento, Because Magento order %s is in different state.'%(order_name, increment_id)
						elif opr == "invoice":
							try:
								mage_invoice = server.call(session,'magerpsync.order_invoice', [increment_id, "Invoiced From Odoo", email])
								text = 'Invoice of order %s has been sucessfully updated on magento.'%order_name
								status = 'yes'
							except Exception,e:
								text = 'Magento Invoicing Error For Order %s , Error %s.'%(order_name, e)
				self._cr.commit()
				self.env['magento.sync.history'].create({'status':status,'action_on':'order','action':'b','error_message':text})
		return mage_shipment


class DeliveryCarrier(models.Model):
	_inherit = 'delivery.carrier'
	
	@api.model
	def create(self, vals):
		if self._context.has_key('magento'):
			vals['name'] = _unescape(vals['name'])
			vals['partner_id'] = self.env['res.users'].browse(self._uid).company_id.partner_id.id
			vals['product_id'] = self.env['product.product'].create({'name':_unescape(vals['name']),'type':'service'}).id
		return super(DeliveryCarrier, self).create(vals)

class AccountInvoice(models.Model):
	_inherit = 'account.invoice'

	@api.multi
	def mage_invoice_trigger(self):
		sale_obj = self.env['sale.order']
		enable_order_invoice = self.env['ir.values'].get_default('mob.config.settings', 'mob_sale_order_invoice')
		for inv_obj in self:
			invoices = inv_obj.read(['origin','state'])
			if invoices[0]['origin']:
				sale_ids = sale_obj.search([('name','=',invoices[0]['origin'])])
				for sale_order_obj in sale_ids:
					order_id = self.env['wk.order.mapping'].search([('erp_order_id','=',sale_order_obj.id)])
					if order_id and sale_order_obj.ecommerce_channel == "magento" and enable_order_invoice and sale_order_obj.is_invoiced:
						sale_order_obj.manual_magento_order_operation("invoice")
		return True

Carrier_Code = [
					('custom', 'Custom Value'),
					('dhl', 'DHL (Deprecated)'),
					('fedex', 'Federal Express'),
					('ups', 'United Parcel Service'),
					('usps', 'United States Postal Service'),
					('dhlint', 'DHL')
				]

class StockPicking(models.Model):
	_inherit = "stock.picking"

	carrier_code = fields.Selection(Carrier_Code, string='Magento Carrier', default="custom", help="Magento Carrier")
	magento_shipment = fields.Char(string='Magento Shipment', help="Contains Magento Order Shipment Number (eg. 300000008)")

	@api.multi
	def do_transfer(self):
		res = super(StockPicking, self).do_transfer()
		sale_order_obj = self.sale_id
		enable_order_shipment = self.env['ir.values'].get_default('mob.config.settings', 'mob_sale_order_shipment')
		if sale_order_obj.is_shipped and sale_order_obj.ecommerce_channel == "magento" and enable_order_shipment:
			sale_order_obj.manual_magento_order_operation("shipment")
		return res

	@api.multi
	def action_sync_tracking_no(self):
		text = ''
		for stock_obj in self:
			sale_id = stock_obj.sale_id.id
			magento_shipment = stock_obj.magento_shipment
			carrier_code = stock_obj.carrier_code
			carrier_tracking_no = stock_obj.carrier_tracking_ref
			if not carrier_tracking_no:
				raise UserError('Warning! Sorry No Carrier Tracking No. Found!!!')
			elif not carrier_code:
				raise UserError('Warning! Please Select Magento Carrier!!!')
			carrier_title = dict(Carrier_Code)[carrier_code]
			map_ids = self.env['wk.order.mapping'].search([('erp_order_id','=',sale_id)])
			if map_ids:
				obj = map_ids[0].instance_id
				url = obj.name + XMLRPC_API
				user = obj.user
				pwd = obj.pwd
				email = obj.notify
				try:
					server = xmlrpclib.Server(url)
					session = server.login(user,pwd)
				except xmlrpclib.Fault, e:
					text = 'Error, %s Magento details are Invalid.'%e
				except IOError, e:
					text = 'Error, %s.'%e
				except Exception,e:
					text = 'Error in Magento Connection.'
				if session:
					track_array = [magento_shipment, carrier_code, carrier_title, carrier_tracking_no]
					try:
						mage_track = server.call(session,'sales_order_shipment.addTrack', track_array)
						text = 'Tracking number successfully added.'
					except xmlrpclib.Fault, e:
						text = "Error While Syncing Tracking Info At Magento. %s"%e
				partial = self.env['message.wizard'].create({'text':text})
				return { 'name': ("Information"),
					 'view_mode': 'form',
					 'view_type': 'form',
					 'res_model': 'message.wizard',
					 'view_id': self.env.ref('magento_bridge.message_wizard_form1').id,
					 'res_id': partial.id,
					 'type': 'ir.actions.act_window',
					 'nodestroy': True,
					 'target': 'new',
			 	}


# END