# -*- coding: utf-8 -*-
#################################################################################
#
#    Copyright (c) 2015-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
#
#################################################################################

import re
import openerp
import xmlrpclib
from openerp.addons.base.res.res_partner import _lang_get
from openerp import api, fields, models, _
from openerp.exceptions import UserError

XMLRPC_API = '/index.php/api/xmlrpc'

def _unescape(text):
	##
	# Replaces all encoded characters by urlib with plain utf8 string.
	#
	# @param text source text.
	# @return The plain text.
	from urllib import unquote_plus
	try:
		text = unquote_plus(text.encode('utf8'))
		return text
	except Exception, e:
		return text

class MagentoConfigure(models.Model):
	_name = "magento.configure"
	_inherit = ['mail.thread']
	_description = "Magento Configuration"
	_rec_name = 'instance_name'

	def _default_instance_name(self):
		return self.env['ir.sequence'].get('magento.configure')

	def _default_category(self):
		if 'categ_id' in self._context and self._context['categ_id']:
			return self._context['categ_id']		
		try:
			return self.env['ir.model.data'].get_object_reference('product', 'product_category_all')[1]
		except ValueError:
			return False

	def _fetch_magento_store(self, url, session):
		stores = []
		store_info = {}
		try:
			server = xmlrpclib.Server(url)
			stores = server.call(session, 'store.list')
		except xmlrpclib.Fault, e:
			raise UserError(_('Error!\nError While Fetching Magento Stores!!!, %s')%e)
		for store in stores:
			if store['website']['is_default'] == '1':				
				store_info['website_id'] = int(store['website']['website_id'])
				store_obj = self.env['magento.store.view']._get_store_view(store)
				store_info['store_id'] = store_obj.id
				break;
		return store_info

	name = fields.Char(string='Base URL', required=True)
	instance_name = fields.Char(string='Instance Name', default=lambda self: self._default_instance_name())
	user = fields.Char(string='API User Name', required=True)
	pwd = fields.Char(string='API Password',required=True, size=100)
	status = fields.Char(string='Connection Status', default=lambda *a: 1, readonly=True)
	active = fields.Boolean(string="Active", default=True)
	store_id = fields.Many2one('magento.store.view', string='Default Magento Store')
	group_id = fields.Many2one(related="store_id.group_id", string="Default Store", readonly=True, store=True)
	website_id = fields.Many2one(related="group_id.website_id", string="Default Magento Website", readonly=True)
	credential = fields.Boolean(string="Show/Hide Credentials Tab", default=lambda *a: 1, help="If Enable, Credentials tab will be displayed, "
							"And after filling the details you can hide the Tab.")
	notify = fields.Boolean(string='Notify Customer By Email', default=lambda *a: 1, help="If True, customer will be notify" 
								"during order shipment and invoice, else it won't.")
	language = fields.Selection(_lang_get,string="Default Language", default=api.model(lambda self: self.env.lang),
										help="Selected language is loaded in the system, "
											"all documents related to this contact will be synched in this language.")
	category = fields.Many2one('product.category', string="Default Category", default=lambda self: self._default_category(), 
										help="Selected Category will be set default category for odoo's product, "
											"in case when magento product doesn\'t belongs to any catgeory.")
	state = fields.Selection([('enable','Enable'),('disable','Disable')], string='Status', default="enable", help="status will be consider during order invoice, "
							"order delivery and order cancel, to stop asynchronous process at other end.", size=100)
	inventory_sync = fields.Selection([	('enable','Enable'),('disable','Disable')], string='Inventory Update', default="enable", 
										help="If Enable, Invetory will Forcely Update During Product Update Operation.", size=100)
	warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse', default=lambda self: self.env['sale.order']._default_warehouse_id(), help="Used During Inventory Synchronization From Magento to Odoo.")
	location_id = fields.Many2one(related='warehouse_id.lot_stock_id', string='Location')
	create_date = fields.Datetime(string='Created Date')
	correct_mapping = fields.Boolean(string='Correct Mapping',default=True)

	@api.model
	def create(self, vals):
		active_ids = self.search([('active','=',True)])		
		if vals['active'] and active_ids:
			raise UserError(_('Warning!\nSorry, Only one active connection is allowed.'))
		vals['instance_name'] = self.env['ir.sequence'].get('magento.configure')
		return super(MagentoConfigure, self).create(vals)

	@api.multi
	def write(self, vals):
		active_ids = self.search([('active','=',True)])		
		if vals:
			if len(active_ids)>0 and vals.has_key('active') and vals['active']:
				raise UserError(_('Warning!\nSorry, Only one active connection is allowed.'))
			for instance_value in self:
				if instance_value.instance_name == None or instance_value.instance_name == False:
					vals['instance_name'] = self.env['ir.sequence'].get('magento.configure')
		return super(MagentoConfigure, self).write(vals)

	@api.multi	
	def set_default_magento_website(self, url, session):
		for obj in self:
			store_id = obj.store_id
			ctx = dict(self._context or {})
			ctx['instance_id'] = obj.id
			if not store_id:
				store_info = self.with_context(ctx)._fetch_magento_store(url, session)
				if store_info:
					self.write(store_info)
				else:
					raise UserError(_('Error!\nMagento Default Website Not Found!!!'))
		return True

	#############################################
	##    		magento connection		   	   ##
	#############################################
	@api.multi
	def test_connection(self):
		session = 0
		status = 'Magento Connection Un-successful'
		text = 'Test connection Un-successful please check the magento api credentials!!!'
		url = self.name + XMLRPC_API
		user = self.user
		pwd = self.pwd
		check_mapping = self.correct_mapping
		try:
			server = xmlrpclib.Server(url)
			session = server.login(user, pwd)
		except xmlrpclib.Fault, e:
			text = "Error, %s Invalid Login Credentials!!!"%(e.faultString)
		except IOError, e:
			text = str(e)
		except Exception,e:
			text = "Magento Connection Error in connecting: %s"%(e)
		if session:
			store_id = self.set_default_magento_website(url, session)
			text = 'Test Connection with magento is successful, now you can proceed with synchronization.'
			status = "Congratulation, It's Successfully Connected with Magento Api."
		self.status = status
		partial = self.env['message.wizard'].create({'text':text})
		if check_mapping:
			self.correct_instance_mapping()
		
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

	@api.model
	def _create_connection(self):
		""" create a connection between Odoo and magento 
			returns: False or list"""
		session = 0
		instance_id = 0
		if self._context.has_key('instance_id'):
			instance_id = self.browse(self._context.get('instance_id'))
		else:
			config_id = self.search([('active','=',True)])
			if len(config_id) > 1:
				raise UserError(_('Error!\nSorry, only one Active Configuration setting is allowed.'))
			if not config_id:
				raise UserError(_('Error!\nPlease create the configuration part for Magento connection!!!'))
			else:
				instance_id = config_id[0]
		if instance_id:
			url = instance_id.name + XMLRPC_API
			user = instance_id.user
			pwd = instance_id.pwd
			if instance_id.language:
				ctx = dict(self._context or {})
				ctx['lang'] = instance_id.language
			try:
				server = xmlrpclib.Server(url)
				session = server.login(user, pwd)
			except xmlrpclib.Fault, e:
				raise UserError(_('Error, %s!\nInvalid Login Credentials!!!')%e.faultString)
			except IOError, e:
				raise UserError(_('Error!\n %s')% e)
			except Exception,e:
				raise UserError(_('Error!\nMagento Connection Error in connecting: %s') % e)
			if session:
				return [url, session, instance_id.id]
			else:
				return False

	@api.model
	def fetch_connection_info(self, vals):
		"""
			Called by Xmlrpc from Magento
		"""
		if vals.has_key('magento_url'):
			mage_url = re.sub(r'^https?:\/\/', '', vals.get('magento_url'))
			active_connection_ids = self.search([('active','=',True)])
			for odoo_obj in active_connection_ids:
				act = odoo_obj.name
				act = re.sub(r'^https?:\/\/', '', act)
				mage_url = re.split('index.php', mage_url)[0]
				if mage_url == act or mage_url[:-1] == act or act in mage_url:
					return odoo_obj.read(['language', 'category', 'warehouse_id'])[0]
		return False

	@api.model
	def correct_instance_mapping(self):
		self.mapped_status("magento.product")
		self.mapped_status("magento.product.template")
		self.mapped_status("wk.order.mapping")
		self.mapped_status("magento.customers")
		self.mapped_status("magento.product.attribute.value")
		self.mapped_status("magento.product.attribute")
		self.mapped_status("magento.category")
		self.mapped_status("magento.website")
		self.mapped_status("magento.store")
		self.mapped_status("magento.store.view")
		self.mapped_status("magento.attribute.set")
		return True

	@api.model
	def mapped_status(self, model):
		rest_ids = self.env[model].search([('instance_id','=',False)])
		if rest_ids:
			rest_ids.write({'instance_id':self.id})
		return True

class MagentoStoreView(models.Model):
	_name = "magento.store.view"
	_description = "Magento Store View"

	name = fields.Char(string='Store View Name', size=64, required=True)
	code = fields.Char(string='Code', size=64, required=True)
	view_id = fields.Integer(string='Magento Store View Id', readonly=True)
	instance_id = fields.Many2one('magento.configure',string='Magento Instance')
	group_id = fields.Many2one('magento.store',string='Store Id')
	is_active = fields.Boolean(string='Active')
	sort_order = fields.Integer(string='Sort Order')
	create_date = fields.Datetime(string='Created Date', readonly=True)

	@api.multi
	@api.depends('name', 'group_id')
	def name_get(self):
		result = []
		for record in self:
			name = record.name + "\n(%s)"%(record.group_id.name) + "\n(%s)"%(record.group_id.website_id.name)			
			result.append((record.id, name))
		return result

	@api.model
	def _get_store_view(self, store):
		group_id = 0
		instance_id = self._context.get('instance_id')
		views = self.search([('view_id','=',store['store_id']),('instance_id','=',instance_id)])
		if views:
			view_id = views[0]
		else:
			group_id = self.env['magento.store']._get_store_group(store['group'], store['website'])
			view_dict = {
							'name':store['name'],
							'code':store['code'],
							'view_id':store['store_id'],
							'group_id':group_id.id,
							'instance_id':instance_id,
							'is_active': store['is_active'],
							'sort_order': store['sort_order'],
						}
			view_id = self.create(view_dict)			
		return view_id

class MagentoStore(models.Model):
	_name = "magento.store"
	_description = "Magento Store"
	
	name = fields.Char(string='Store Name', size=64, required=True)
	group_id = fields.Integer(string='Magento Store Id', readonly=True)
	instance_id = fields.Many2one('magento.configure',string='Magento Instance')
	root_category_id = fields.Integer(string='Root Category Id', readonly=True)
	default_store_id = fields.Integer(string='Default Store Id')
	website_id = fields.Many2one('magento.website',string='Website')
	create_date = fields.Datetime(string='Created Date', readonly=True)
	
	@api.model
	def _get_store_group(self, group, website):
		group_id = 0
		instance_id = self._context.get('instance_id')
		groups = self.search([('group_id','=',group['group_id']),('instance_id','=',instance_id)])
		if groups:
			group_id = groups[0]
		else:
			website_id = self.env['magento.website']._get_website(website)
			group_dict = {
							'name':group['name'],
							'website_id': website_id.id,
							'group_id': group['group_id'],
							'instance_id':instance_id,
							'root_category_id': group['root_category_id'],
							'default_store_id': group['default_store_id'],
						}
			group_id = self.create(group_dict)
		return group_id

class MagentoWebsite(models.Model):
	_name = "magento.website"
	_description = "Magento Website"
	
	name = fields.Char(string='Website Name', size=64, required=True)
	website_id = fields.Integer(string='Magento Webiste Id', readonly=True)
	instance_id = fields.Many2one('magento.configure',string='Magento Instance')
	code = fields.Char(string='Code', size=64, required=True)
	sort_order = fields.Char(string='Sort Order', size=64)
	is_default = fields.Boolean(string='Is Default', readonly=True)
	default_group_id = fields.Integer(string='Default Store', readonly=True)
	create_date = fields.Datetime(string='Created Date', readonly=True)
	
	@api.model
	def _get_website(self, website):
		website_id = 0
		instance_id = self._context.get('instance_id')		
		websites = self.search([('website_id','=',website['website_id']),('instance_id','=',instance_id)])		
		if websites:
			website_id = websites[0]
		else:
			website_dict = {
							'name':website['name'],
							'code':website['code'],
							'instance_id':instance_id,
							'website_id': website['website_id'],
							'is_default':website['is_default'],
							'sort_order':website['sort_order'],
							'default_group_id':website['default_group_id']
						}
			website_id = self.create(website_dict)			
		return website_id

################### Catalog Mapping Models ########################

class MagentoProductTemplate(models.Model):
	_name="magento.product.template"
	_order = 'id desc'
	_description = "Magento Product Template"
	
	@api.model
	def create(self, vals):
		vals['erp_template_id']=vals['template_name']
		if not vals.has_key('base_price'):
			vals['base_price'] = self.env['product.template'].browse(vals['erp_template_id']).list_price
		return super(MagentoProductTemplate, self).create(vals)

	template_name = fields.Many2one('product.template', string='Template Name')
	erp_template_id = fields.Integer(string='Odoo`s Template Id')
	mage_product_id = fields.Integer(string='Magento`s Product Id')
	instance_id = fields.Many2one('magento.configure',string='Magento Instance')
	base_price = fields.Float(string='Base Price(excl. impact)')
	is_variants = fields.Boolean(string='Is Variants')
	created_by = fields.Char(string='Created By', default="odoo", size=64)
	create_date = fields.Datetime(string='Created Date')
	write_date = fields.Datetime(string='Updated Date')
	need_sync = fields.Selection([('Yes','Yes'),('No','No')],string='Update Required', default="No")


	@api.model
	def create_n_update_attribute_line(self, data):
		line_dict = {}
		price_pool = self.env['product.attribute.price']
		attribute_line = self.env['product.attribute.line']
		if data.has_key('product_tmpl_id'):
			template_id = data.get('product_tmpl_id')
			attribute_id = data.get('attribute_id')
			if data.has_key('values') and data['values']:
				value_ids = []
				for value in data['values']:
					value_id = value['value_id']
					value_ids.append(value_id)
					if value['price_extra']:
						price_extra = value['price_extra']
						search_ids = price_pool.search([('product_tmpl_id','=',template_id), ('value_id','=',value_id)])
						if search_ids:
							for search_obj in search_ids:
								search_obj.write({'price_extra':price_extra})
						else:
							price_pool.create({'product_tmpl_id':template_id,'value_id':value_id, 'price_extra':price_extra})
				line_dict['value_ids'] = [(6, 0, value_ids)]
			search = attribute_line.search([('product_tmpl_id','=',template_id),('attribute_id','=',attribute_id)])
			if search:
				for search_obj in search:
					search_obj.write(line_dict)
			else:
				line_dict['attribute_id'] = attribute_id
				line_dict['product_tmpl_id'] = template_id
				attribute_line.create(line_dict)
			return True
		return False

class MagentoProduct(models.Model):			
	_name="magento.product"
	_order = 'id desc'
	_rec_name = "pro_name"
	_description = "Magento Product"

	pro_name = fields.Many2one('product.product', string='Product Name')
	oe_product_id = fields.Integer(string='Odoo Product Id')
	mag_product_id = fields.Integer(string='Magento Product Id')
	need_sync = fields.Selection([('Yes', 'Yes'),('No', 'No')],string='Update Required', default='No')
	instance_id = fields.Many2one('magento.configure',string='Magento Instance')
	create_date = fields.Datetime(string='Created Date')
	write_date = fields.Datetime(string='Updated Date')
	created_by = fields.Char(string='Created By', default='odoo', size=64)

class MagentoCategory(models.Model):
	_name = "magento.category"
	_order = 'id desc'
	_rec_name = "cat_name"
	_description = "Magento Category"

	cat_name = fields.Many2one('product.category', string='Category Name')
	oe_category_id = fields.Integer(string='Odoo Category Id')
	mag_category_id = fields.Integer(string='Magento Category Id')
	instance_id = fields.Many2one('magento.configure',string='Magento Instance')
	need_sync = fields.Selection([('Yes', 'Yes'),('No', 'No')], string='Update Required', default="No")
	create_date = fields.Datetime(string='Created Date')
	write_date = fields.Datetime(string='Updated Date')
	created_by = fields.Char(string='Created By', default="odoo", size=64)
	
	@api.model
	def create_category(self, data):
		"""Create and update a category by any webservice like xmlrpc.
		@param data: details of category fields in list.
		"""	
		categ_dic = {}		
		category_id = 0
		if data.has_key('name') and data['name']:
			categ_dic['name'] = _unescape(data.get('name'))
			
		if data.has_key('type'):
			categ_dic['type'] = data.get('type')
		if data.has_key('parent_id'):
			categ_dic['parent_id'] = data.get('parent_id')
		if data.get('method') == 'create':
			mage_category_id = data.get('mage_id')
			category_id = self.env['product.category'].create(categ_dic)
			self.create({'cat_name':category_id.id,'oe_category_id':category_id.id,'mag_category_id':mage_category_id,'instance_id':self._context.get('instance_id'),'created_by':'Magento'})
			return category_id.id
		if data.get('method') == 'write':
			category_id = data.get('category_id')
			categ_obj = self.env['product.category'].browse(category_id)
			categ_obj.write(categ_dic)
			return True
		return False

class MagentoAttributeSet(models.Model):
	_name = "magento.attribute.set"
	_description = "Magento Attribute Set"
	_order = 'id desc'

	name = fields.Char(string='Magento Attribute Set')
	attribute_ids = fields.Many2many('product.attribute', 'product_attr_set','set_id','attribute_id',string='Product Attributes', readonly=True, help="Magento Set attributes will be handle only at magento.")
	instance_id = fields.Many2one('magento.configure',string='Magento Instance')
	set_id = fields.Integer(string='Magento Set Id', readonly=True)
	created_by = fields.Char(string='Created By', default="odoo", size=64)
	create_date = fields.Datetime(string='Created Date')
	write_date = fields.Datetime(string='Updated Date')

	@api.model
	def create(self, vals):
		if self._context.has_key('instance_id'):
			vals['instance_id'] = self._context.get('instance_id')
		return super(MagentoAttributeSet, self).create(vals)

class MagentoProductAttribute(models.Model):
	_name = "magento.product.attribute"
	_order = 'id desc'
	_description = "Magento Product Attribute"


	@api.model
	def create(self, vals):
		vals['erp_id'] = vals['name']
		if self._context.has_key('instance_id'):
			vals['instance_id'] = self._context.get('instance_id')
		return super(MagentoProductAttribute, self).create(vals)
	
	@api.multi
	def write(self,vals):
		if vals.has_key('name'):
			vals['erp_id']=vals['name']
		if self._context.has_key('instance_id'):
			vals['instance_id'] = self._context.get('instance_id')	
		return super(MagentoProductAttribute, self).write(vals)
	
	name = fields.Many2one('product.attribute', string='Product Attribute')
	erp_id = fields.Integer(string='Odoo`s Attribute Id')
	mage_id = fields.Integer(string='Magento`s Attribute Id')
	instance_id = fields.Many2one('magento.configure', string='Magento Instance')
	created_by = fields.Char(string='Created By', default="odoo", size=64)
	create_date = fields.Datetime(string='Created Date')
	write_date = fields.Datetime(string='Updated Date')

class MagentoProductAttributeValue(models.Model):
	_name="magento.product.attribute.value"
	_order = 'id desc'
	_description = "Magento Product Attribute Value"
	
	@api.model	
	def create(self, vals):
		vals['erp_id'] = vals['name']
		if self._context.has_key('instance_id'):
			vals['instance_id'] = self._context.get('instance_id')	
		return super(MagentoProductAttributeValue, self).create(vals)
	
	@api.multi
	def write(self, vals):
		if vals.has_key('name'):
			vals['erp_id'] = vals['name']
		if self._context.has_key('instance_id'):
			vals['instance_id'] = self._context.get('instance_id')
		return super(MagentoProductAttributeValue,self).write(vals)
		
	name = fields.Many2one('product.attribute.value', string='Attribute Value')
	erp_id = fields.Integer(string='Odoo Attribute Value Id')
	mage_id = fields.Integer(string='Magento Attribute Value Id')
	instance_id = fields.Many2one('magento.configure',string='Magento Instance')
	created_by = fields.Char(string='Created By', default="odoo", size=64)
	create_date = fields.Datetime(string='Created Date')
	write_date = fields.Datetime(string='Updated Date')


	################### Catalog Mapping Models End ########################

	############## Magento Customer Mapping Models ################

class MagentoCustomers(models.Model):			
	_name="magento.customers"
	_order = 'id desc'
	_rec_name = "cus_name"
	_description = "Magento Customers"
	
	cus_name = fields.Many2one('res.partner', string='Customer Name')
	oe_customer_id = fields.Integer(string='Odoo Customer Id')
	mag_customer_id = fields.Char(string='Magento Customer Id',size=50)
	instance_id = fields.Many2one('magento.configure', string='Magento Instance')
	mag_address_id = fields.Char(string='Magento Address Id', size=50)
	need_sync = fields.Selection([('Yes', 'Yes'),('No', 'No')], default="No", string='Update Required')
	created_by = fields.Char(string='Created By', default="odoo", size=64)
	create_date = fields.Datetime(string='Created Date')
	write_date = fields.Datetime(string='Updated Date')

class MagentoRegion(models.Model):			
	_name="magento.region"
	_order = 'id desc'
	_description = "Magento Region"	

	name = fields.Char(string='Region Name',size=100)
	mag_region_id = fields.Integer(string='Magento Region Id')
	country_code = fields.Char(string='Country Code',size=10)
	region_code = fields.Char(string='Region Code',size=10)
	created_by = fields.Char(string='Created By', default="odoo", size=64)
	create_date = fields.Datetime(string='Created Date')
	write_date = fields.Datetime(string='Updated Date')

	############# Customer Model End #############################

class MagentoSyncHistory(models.Model):
	_name ="magento.sync.history"
	_order = 'id desc'
	_description = "Magento Synchronization History"

	status = fields.Selection((('yes','Successfull'),('no','Un-Successfull')), string='Status')
	action_on = fields.Selection((('product','Product'),('category','Category'),('customer','Customer'),('order','Order')),string='Action On')
	action = fields.Selection((('a','Import'),('b','Export'),('c','Update')),string='Action')
	create_date = fields.Datetime(string='Created Date')
	error_message = fields.Text(string='Summary')
# END