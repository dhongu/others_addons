# -*- coding: utf-8 -*-
#################################################################################
#
#    Copyright (c) 2015-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
#
#################################################################################

import xmlrpclib
from openerp import api, fields, models, _
from openerp.exceptions import UserError

XMLRPC_API = '/index.php/api/xmlrpc'

class MagentoSynchronization(models.Model):
	_name = "magento.synchronization"
	_description = "Magento Synchronization"

	@api.one
	def open_configuration(self):
		view_id = False
		setting_ids = self.env['magento.configure'].search([('active','=',True)])
		if setting_ids:
			view_id = setting_ids[0].id
		return {
				'type': 'ir.actions.act_window',
				'name': 'Configure Magento Api',
				'view_type': 'form',
				'view_mode': 'form',
				'res_model': 'magento.configure',
				'res_id': view_id,
				'target': 'current',
				'domain': '[]',
			}

	@api.model
	def sync_attribute_set(self, data):
		erp_set_id = 0
		set_dic = {}
		res = False
		set_env = self.env['magento.attribute.set']
		if data.has_key('name') and data.get('name'):
			set_map_ids = set_env.search([('name','=',data.get('name'))])
			if not set_map_ids:
				set_dic['name'] = data.get('name')
				if data.has_key('set_id') and data.get('set_id'):
					set_dic['set_id'] = data.get('set_id')
				set_dic['created_by'] = 'Magento'
				set_dic['instance_id'] = self._context.get('instance_id')
				erp_set_id = set_env.create(set_dic)
			else:
				erp_set_id = set_map_ids[0]
			if erp_set_id: 
				if data.has_key('set_id') and data.get('set_id'):
					dic = {}
					dic['set_id'] = data.get('set_id')
					if data.has_key('attribute_ids') and data.get('attribute_ids'):
						dic['attribute_ids'] = [(6, 0, data.get('attribute_ids'))]
					else:
						dic['attribute_ids'] = [[5]]
					if self._context.has_key('instance_id') and self._context['instance_id']:
						dic['instance_id'] = self._context.get('instance_id')
					res = erp_set_id.write(dic)
		return res

	@api.model
	def server_call(self, session, url, method, params=None):		
		if session:
			server = xmlrpclib.Server(url)
			mage_id = 0			
			try:
				if params is None:
					mage_id = server.call(session, method)					
				else:
					mage_id = server.call(session, method, params)
			except xmlrpclib.Fault, e:
				name = ""
				return [0,'\nError in create (Code: %s).%s'%(name,str(e))]
			return [1, mage_id]

	#############################################
	## 	 Export Attributes and values          ##
	#############################################
	@api.multi
	def export_attributes_and_their_values(self):
		map_dic = []
		map_dict = {}
		error_message = ''
		attribute_count = 0
		attribute_pool = self.env['product.attribute']
		attribute_value_pool = self.env['product.attribute.value']
		attribute_mapping_pool = self.env['magento.product.attribute']
		value_mapping_pool = self.env['magento.product.attribute.value']
		connection = self.env['magento.configure']._create_connection()		
		if connection:
			url = connection[0]
			session = connection[1]
			ctx = dict(self._context or {})
			ctx['instance_id'] = instance_id = connection[2]
			# self._context['instance_id'] = instance_id = connection[2]
			attribute_map_ids = attribute_mapping_pool.with_context(ctx).search([('instance_id','=',instance_id)])
			for attribute_map_obj in attribute_map_ids:
				map_dic.append(attribute_map_obj.erp_id)
				map_dict.update({attribute_map_obj.erp_id:attribute_map_obj.mage_id})
			attribute_ids = attribute_pool.search([])
			if attribute_ids:
				for attribute_obj in attribute_ids:
					if attribute_obj.id not in map_dic:
						name = attribute_obj.name
						label = attribute_obj.name
						attribute_response = self.with_context(ctx).create_product_attribute(url, session, attribute_obj.id , name, label)
					else:
						mage_id = map_dict.get(attribute_obj.id)
						attribute_response = [1, int(mage_id)]
					if attribute_response[0] == 0:
						error_message = error_message + attribute_response[1]
					if attribute_response[0] > 0:
						mage_id = attribute_response[1]
						for value_obj in attribute_obj.value_ids:
							if not value_mapping_pool.with_context(ctx).search([('erp_id','=',value_obj.id),('instance_id','=',instance_id)]):
								name = value_obj.name
								position = value_obj.sequence
								value_response = self.with_context(ctx).create_attribute_value(url, session, mage_id, value_obj.id, name, position)
								if value_response[0] == 0:
									error_message = error_message + value_response[1]
						attribute_count += 1
			else:
				error_message = "No Attribute(s) Found To Be Export At Magento!!!"
			if attribute_count:
				error_message += "\n %s Attribute(s) and their value(s) successfully Synchronized To Magento."%(attribute_count)
			partial = self.env['message.wizard'].with_context(ctx).create({'text':error_message})
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
	def create_product_attribute(self, url, session, attribute_id, name, label):
		name = name.lower().replace(" ","_").replace("-","_")
		name = name.strip()
		if session:
			attrribute_data = {
					'attribute_code':name,
					'scope':'global',
					'frontend_input':'select',
					'is_configurable':1,
					'is_required':1,
					'frontend_label':[{'store_id':0,'label':label}]
				}
			mage_attribute_id = 0
			mage_id = self.server_call(session, url, 'product_attribute.create', [attrribute_data])
			if mage_id[0] > 0:
				mage_attribute_id = mage_id[1]
			else:
				attribute_data = self.server_call(session, url, 'product_attribute.info', [name])
				if attribute_data[0] > 0:
					mage_attribute_id = attribute_data[1]['attribute_id']
					mage_id = [1, mage_attribute_id]
				else:
					return mage_id
			erp_map_data = {
					'name':attribute_id, 
					'erp_id':attribute_id, 
					'mage_id':mage_attribute_id,
					'instance_id':self._context.get('instance_id'),
				}	
			self.env['magento.product.attribute'].create(erp_map_data)
			mage_map_data = {
								'name':name, 
								'mage_attribute_id':mage_attribute_id,
								'erp_attribute_id':attribute_id
							}
			self.server_call(session, url, 'magerpsync.attribute_map', [mage_map_data])
			return mage_id

	@api.model
	def create_attribute_value(self, url, session, mage_attr_id, erp_attr_id, name, position='0'):
		if session:
			name = name.strip()
			options_data = {
						'label':[{'store_id':0, 'value':name}],
						'order':position,
						'is_default':0
					}
			mage_id = self.server_call(session, url, 'product_attribute.addOption', [mage_attr_id, options_data])
			if mage_id[0] > 0:
				erp_map_data = {
								'name':erp_attr_id,
								'erp_id':erp_attr_id,
								'mage_id':mage_id[1],
								'instance_id':self._context.get('instance_id')
								}
				self.env['magento.product.attribute.value'].create(erp_map_data)
				mage_map_data = {
								'name':name, 
								'mage_attribute_option_id':int(mage_id[1]),
								'erp_attribute_option_id':erp_attr_id
								}				
				self.server_call(session, url, 'magerpsync.attributeoption_map', [mage_map_data])
				return mage_id
			else:
				return mage_id

	@api.model
	def assign_attribute_Set(self, template_ids):
		connection = self.env['magento.configure']._create_connection()
		if connection:
			success_ids = []
			for temp_obj in template_ids:
				attribute_line_ids = temp_obj.attribute_line_ids
				set_obj = self.get_default_attribute_set()
				if attribute_line_ids:
					set_obj = self.get_magento_attribute_set(attribute_line_ids)
				if set_obj:
					temp_obj.write({'attribute_set_id':set_obj.id})
					success_ids.append(temp_obj.id)
		else:
			raise UserError(_("Connection Error!\nError in Odoo Connection"))
		return True

	@api.model
	def get_default_attribute_set(self):
		default_search = self.env['magento.attribute.set'].search([('set_id','=',4),('instance_id','=', self._context['instance_id'])])
		if default_search:
			return default_search[0]
		else:
			raise UserError(_('Information!\nDefault Attribute set not Found, please sync all Attribute set from Magento!!!'))

	@api.model
	def get_magento_attribute_set(self, attribute_line_ids):
		flag = False
		attribute_ids = []
		template_attribute_ids = []
		mage_set_env = self.env['magento.attribute.set']
		for attr in attribute_line_ids:
			template_attribute_ids.append(attr.attribute_id.id)			
		set_ids = mage_set_env.search([('instance_id','=', self._context['instance_id'])], order="set_id asc")		
		for set_obj in set_ids:
			set_attribute_ids = set_obj.attribute_ids.ids			
			common_attributes = list(set(set_attribute_ids) & set(template_attribute_ids))
			template_attribute_ids.sort()
			if common_attributes == template_attribute_ids:
				return set_obj
		return False

	#############################################
	##    	Start Of Category Synchronizations ##
	#############################################


	#############################################
	##    		Export/Update Categories   	   ##
	#############################################
	
	def get_map_category_ids(self, category_ids):
		product_category_ids = []		
		mage_cat_env = self.env['magento.category']
		map_ids = mage_cat_env.search([('instance_id','=', self._context['instance_id'])])
		for map_obj in map_ids:
			product_category_ids.append(map_obj.cat_name)
		erp_category_ids = list(set(category_ids) | set(product_category_ids))
		erp_category_ids = list(set(erp_category_ids) ^ set(product_category_ids))
		return erp_category_ids
	
	def get_update_category_ids(self, category_ids):
		map_category_ids = []
		mage_cat_env = self.env['magento.category']
		map_ids = mage_cat_env.search([('need_sync','=','Yes'),('mag_category_id','!=',-1),('instance_id','=', self._context['instance_id'])])		
		for map_obj in map_ids:
			if map_obj.cat_name in category_ids:
				map_category_ids.append(map_obj)
		return map_category_ids

	@api.multi
	def export_categories_check(self):
		text = text1 = text2= ''
		up_error_ids = []
		success_ids = []
		success_up_ids = []
		category_ids = []
		connection = self.env['magento.configure']._create_connection()
		if connection:
			mage_cat_pool = self.env['magento.category']
			mage_sync_history = self.env['magento.sync.history']
			url = connection[0]
			session = connection[1]
			ctx = dict(self._context or {})
			instance_id = ctx['instance_id'] = connection[2]			
			if self._context.has_key('active_model') and self._context.get('active_model') == "product.category":
				categ_ids = self._context.get('active_ids')
				for categ_id in self.env['product.category'].browse(categ_ids):
					category_ids.append(categ_id)
			else:
				category_ids = self.env['product.category'].with_context(ctx).search([])

			if self._context.has_key('sync_opr') and self._context['sync_opr'] == 'export':
				erp_category_ids = self.with_context(ctx).get_map_category_ids(category_ids)
				if not erp_category_ids:
					raise UserError(_('Information!\nAll category(s) has been already exported on magento.'))
				for erp_category_id in erp_category_ids:
					categ_id = self.with_context(ctx).sync_categories(url, session, erp_category_id)
					if categ_id:
						success_ids.append(categ_id)
						text = "\nThe Listed category ids %s has been created on magento."%(success_ids)
						mage_sync_history.create({'status':'yes','action_on':'category','action':'b','error_message':text})
			
			if self._context.has_key('sync_opr') and self._context['sync_opr'] == 'update':
				update_map_ids = self.with_context(ctx).get_update_category_ids(category_ids)
				if not update_map_ids:
					raise UserError(_('Information!\nAll category(s) has been already updated on magento.'))
				cat_update = self.with_context(ctx)._update_specific_category(update_map_ids, url, session)
				if cat_update:
					if cat_update[0] != 0:
						success_up_ids.append(cat_update[1])
						text1 = '\nThe Listed category ids %s has been successfully updated to Magento. \n'%success_up_ids
						mage_sync_history.create({'status':'yes','action_on':'category','action':'c','error_message':text1})
					else:
						up_error_ids.append(cat_update[1])
						text2 = '\nThe Listed category ids %s does not updated on magento.'%up_error_ids
						mage_sync_history.create({'status':'no','action_on':'category','action':'c','error_message':text2})

			partial = self.env['message.wizard'].create({'text':text+text1+text2})
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
		########## update specific category ##########
	
	def _update_specific_category(self, update_map_ids, url, session):
		cat_mv = False
		get_category_data = {}
		category_ids = []
		cat_pool = self.env['magento.category']
		for cat_obj in update_map_ids:
			obj_cat = cat_obj.cat_name
			mage_id = cat_obj.mag_category_id
			mag_parent_id = 1
			if obj_cat and mage_id:
				category_ids.append(obj_cat.id)
				get_category_data['name'] = obj_cat.name
				get_category_data['available_sort_by'] = 1
				get_category_data['default_sort_by'] = 1
				parent_id = obj_cat.parent_id or False
				if parent_id:
					search = cat_pool.search([('cat_name','=',parent_id.id),('instance_id','=', self._context['instance_id'])])
					if search:
						mag_parent_id = search[0].mag_category_id or 1
					else:
						mag_parent_id = self.sync_categories(url, session, parent_id)
				update_data = [mage_id, get_category_data]
				move_data = [mage_id, mag_parent_id]
				self.server_call(session, url, 'catalog_category.update', update_data)				
				self.server_call(session, url, 'catalog_category.move', move_data)
				cat_obj.write({'need_sync':'No'})
		return [1, category_ids]

	def sync_categories(self, url, session, erp_category_id):
		map_category_obj = self.env['magento.category']
		instance_id = 0
		if self._context.has_key('instance_id'):
			instance_id = self._context['instance_id']
		else:
			connection = self.env['magento.configure']._create_connection()
			if connection:
				instance_id = connection[2]
		if erp_category_id:
			map_category_ids = map_category_obj.search([('cat_name','=',erp_category_id.id),('instance_id','=',instance_id)])
			if not map_category_ids:
				name = erp_category_id.name
				if erp_category_id.parent_id:
					p_cat_id = self.sync_categories(url, session, erp_category_id.parent_id)
				else:
					p_cat_id = self.create_category(url, session, erp_category_id.id, 1, name)
					if p_cat_id[0] > 0:
						return p_cat_id[1]
					else:
						return False
				category_id = self.create_category(url, session, erp_category_id.id, p_cat_id, name)
				if category_id[0] > 0:
					return category_id[1]
				else:
					False
			else:
				mage_id = map_category_ids[0].mag_category_id
				return mage_id
		else:
			return False

	def create_category(self, url, session, catg_id, parent_id, catgname):
		if catg_id < 1:
			return False

		catgdetail = dict({
			'name':catgname,
			'is_active':1,
			'available_sort_by':1,
			'default_sort_by' : 1,
			'is_anchor' : 1,
			'include_in_menu' : 1
		})
		updatecatg = [parent_id,catgdetail]	
		mage_cat = self.server_call(session, url, 'catalog_category.create', updatecatg)		
		if mage_cat[0] > 0:
			##########  Mapping Entry  ###########
			self.env['magento.category'].create({'cat_name':catg_id,'oe_category_id':catg_id,'mag_category_id':mage_cat[1],'created_by':'odoo','instance_id': self._context.get('instance_id')})
			self.server_call(session, url, 'magerpsync.category_map', [{'mage_category_id':mage_cat[1],'erp_category_id':catg_id}])
		return mage_cat


	
	#############################################
	##    	End Of Category Synchronizations   ##
##########################################################

##########################################################
	##    	Start Of Product Synchronizations  ##
	#############################################

	#############################################
	##    		export all products		       ##
	#############################################
	
	@api.model
	def get_map_template_ids(self, product_template_ids):		
		template_ids = []
		update_template_map_ids = []
		mage_product_obj = self.env['magento.product.template']
		if self._context.has_key('sync_opr') and self._context['sync_opr'] == 'export':
			map_ids = mage_product_obj.search([('instance_id','=',self._context['instance_id'])])	
			for map_obj in map_ids:
				erp_template_id = map_obj.erp_template_id
				template_ids.append(erp_template_id)
			not_mapped_template_ids = list(set(product_template_ids) | set(template_ids))
			not_mapped_template_ids = list(set(not_mapped_template_ids) ^ set(template_ids))
			return not_mapped_template_ids
		if self._context.has_key('sync_opr') and self._context['sync_opr'] == 'update':
			for product_template_id in product_template_ids:
				map_ids = mage_product_obj.search([('instance_id','=',self._context['instance_id']),('need_sync','=','Yes'),('template_name','=',product_template_id)])
				if map_ids:
					update_template_map_ids.append(map_ids[0])
			return update_template_map_ids
		return False

	#############################################
	##  export bulk/selected products template ##
	#############################################

	@api.multi
	def export_product_check(self):
		text = text1 = text2= ''
		up_error_ids = []
		success_ids = []
		error_ids = []
		success_exp_ids = []
		success_up_ids = []
		template_ids = []
		not_mapped_template_ids = 0
		update_mapped_template_ids = 0
		connection = self.env['magento.configure']._create_connection()
		if connection:
			mage_sync_history = self.env['magento.sync.history']
			template_obj = self.env['product.template']
			url = connection[0]
			session = connection[1]
			ctx = dict(self._context or {})
			instance_id = ctx['instance_id'] = connection[2]			
			pro_dt = len(self.env['product.attribute'].with_context(ctx).search([]))
			map_dt = len(self.env['magento.product.attribute'].with_context(ctx).search([('instance_id','=', instance_id)]))
			pro_op = len(self.env['product.attribute.value'].with_context(ctx).search([]))
			map_op = len(self.env['magento.product.attribute.value'].with_context(ctx).search([('instance_id','=',instance_id)]))		
			if pro_dt != map_dt or pro_op != map_op:
				raise UserError(('Warning!\nPlease, first map all ERP Product attributes and it\'s all options'))
			if self._context.has_key('active_model') and self._context.get('active_model') == "product.template":
				template_ids = self._context.get('active_ids')
			else:
				template_ids = template_obj.search([('type','!=','service')]).ids
			if not template_ids:				
				raise UserError(_('Information!\nNo new product(s) Template found to be Sync.'))
			
			if self._context.has_key('sync_opr') and self._context['sync_opr'] == 'export':
				not_mapped_template_ids = self.with_context(ctx).get_map_template_ids(template_ids)
				if not not_mapped_template_ids:
					raise UserError(_('Information!\nListed product(s) has been already exported on magento.'))
				for template_id in not_mapped_template_ids:
					template_obj = self.env['product.template'].browse(template_id)
					prodtype = template_obj.type
					if prodtype == 'service':
						error_ids.append(template_id)
						continue
					pro = self.with_context(ctx)._export_specific_template(template_obj, url, session)
					if pro:
						if pro[0] > 0:
							success_exp_ids.append(template_obj.id)
						else:
							error_ids.append(pro[1])
					else:
						continue

			if self._context.has_key('sync_opr') and self._context['sync_opr'] == 'update':
				update_mapped_template_ids = self.with_context(ctx).get_map_template_ids(template_ids)
				if not update_mapped_template_ids:
					raise UserError(_('Information!\nListed product(s) has been already updated on magento.'))
				for template_map_obj in update_mapped_template_ids:
					pro_update = self.with_context(ctx)._update_specific_product_template(template_map_obj, url, session)
					if pro_update:
						if pro_update[0] > 0:
							success_up_ids.append(pro_update[1])
						else:
							up_error_ids.append(pro_update[1])
			if success_exp_ids:
				text = "\nThe Listed product(s) %s successfully created on Magento."%(success_exp_ids)
			if error_ids:
				text += '\nThe Listed Product(s) %s does not synchronized on magento.'%error_ids
			if text:
				mage_sync_history.create({'status':'yes','action_on':'product','action':'b','error_message':text})
			if success_up_ids:
				text1 = '\nThe Listed Product(s) %s has been successfully updated to Magento. \n'%success_up_ids
				mage_sync_history.create({'status':'yes','action_on':'product','action':'c','error_message':text1})
			if up_error_ids:
				text2 = '\nThe Listed Product(s) %s does not updated on magento.'%up_error_ids				
				mage_sync_history.create({'status':'no','action_on':'product','action':'c','error_message':text2})
			partial = self.env['message.wizard'].create({'text':text+text1+text2})
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

	#############################################
	##    		Specific template sync	       ##
	#############################################
	
	def _export_specific_template(self, obj_pro, url, session):
		if obj_pro:
			mage_set_id = 0
			instance_id = self._context.get('instance_id')
			ctx = dict(self._context or {})
			get_product_data = {}
			mage_price_changes = {}
			mage_attribute_ids = []
			map_tmpl_pool = self.env['magento.product.template']
			template_id = obj_pro.id
			template_sku = obj_pro.default_code or 'Template Ref %s'%template_id
			if not obj_pro.product_variant_ids:
				return [-2, str(template_id)+' No Variant Ids Found!!!']	
			else:
				if not obj_pro.attribute_set_id.id:					
					self.assign_attribute_Set([obj_pro])
				set_obj = obj_pro.attribute_set_id
				set_obj = self.with_context(ctx)._check_valid_attribute_set(set_obj, template_id)
				wk_attribute_line_ids = obj_pro.attribute_line_ids
				
				if not wk_attribute_line_ids:
					template_sku = 'single_variant'
					mage_ids = self.with_context(ctx)._sync_template_variants(obj_pro, template_sku, url, session)
					name  = obj_pro.name
					price = obj_pro.list_price or 0.0
					if mage_ids:
						erp_map_data = {
										'template_name':template_id,
										'erp_template_id':template_id,
										'mage_product_id':mage_ids[0],
										'base_price':price,
										'is_variants':False,
										'instance_id':instance_id
										}
						check = map_tmpl_pool.with_context(ctx).create(erp_map_data)
						return mage_ids
				else:
					check_attribute = self.with_context(ctx)._check_attribute_with_set(set_obj, wk_attribute_line_ids)
					if check_attribute and check_attribute[0] == -1:
						return check_attribute
					mage_set_id = obj_pro.attribute_set_id.set_id
					if not mage_set_id:
						return [-3, str(template_id)+' Attribute Set Name not found!!!']
					else:
						for type_obj in wk_attribute_line_ids:
							mage_attr_ids = self.with_context(ctx)._check_attribute_sync(type_obj)
							if not mage_attr_ids:
								return [-1, str(template_id)+' Attribute not syned at magento!!!']
							mage_attribute_ids.append(mage_attr_ids[0])
							get_product_data['configurable_attributes'] = mage_attribute_ids
							attrname = type_obj.attribute_id.name.lower().replace(" ","_").replace("-","_")
							val_dic = self.with_context(ctx)._search_single_values(template_id, type_obj.attribute_id.id)
							if val_dic:
								ctx.update(val_dic)
							for value_id in type_obj.value_ids:
								price_extra = 0.0
								##### product template and value extra price ##### 
								price_search = self.env['product.attribute.price'].with_context(ctx).search([('product_tmpl_id','=',template_id),('value_id','=',value_id.id)])
								if price_search:
									price_extra = price_search[0].price_extra
								valuename = value_id.name
								if mage_price_changes.has_key(attrname):
									mage_price_changes[attrname].update({valuename:price_extra})
								else:
									mage_price_changes[attrname] = {valuename:price_extra}
						mage_ids = self.with_context(ctx)._sync_template_variants(obj_pro, template_sku, url, session)
						get_product_data['associated_product_ids'] = mage_ids
						get_product_data['price_changes'] = mage_price_changes						
						get_product_data['visibility'] = 4
						get_product_data['price'] = obj_pro.list_price or 0.00
						get_product_data = self.with_context(ctx)._get_product_array(url, session, obj_pro, get_product_data)
						get_product_data['tax_class_id'] = '0'
						template_sku = 'Template sku %s'%template_id
						newprod_data = ['configurable', mage_set_id, template_sku, get_product_data]
						obj_pro.write({'prod_type':'configurable'})
						mage_product_id = self.server_call(session, url, 'product.create', newprod_data)						
						if mage_product_id[0] > 0:
							self.server_call(session, url, 'product_stock.update', [mage_product_id[1],{'manage_stock':1,'is_in_stock':1}])
							map_tmpl_pool.with_context(ctx).create({'template_name':template_id, 'erp_template_id':template_id, 'mage_product_id':mage_product_id[1], 'base_price': get_product_data['price'], 'is_variants':True, 'instance_id':instance_id})
							self.server_call(session, url, 'magerpsync.template_map', [{'mage_template_id':mage_product_id[1],'erp_template_id':template_id}])
							self.with_context(ctx)._product_attribute_media(url, session, obj_pro, mage_product_id[1] , "create")
							return mage_product_id
						else:
							return [0, str(template_id)+"Not Created at magento"]
		else:
			return False
	
	def _check_valid_attribute_set(self, set_obj, template_id):
		if self._context.has_key('instance_id'):
			instance_id = set_obj.instance_id.id
			if instance_id == self._context['instance_id']:
				return set_obj
			else:
				return False
		else:
			return False

	############# sync template variants ########				
	def _sync_template_variants(self, temp_obj, template_sku, url, session):
		mage_variant_ids = []
		map_prod_env = self.env['magento.product']
		for obj in temp_obj.product_variant_ids:
			search_ids = map_prod_env.search([('pro_name','=', obj.id),('instance_id','=', self._context.get('instance_id'))])
			if search_ids:
				mage_variant_ids.append(search_ids[0].mag_product_id)
			else:
				mage_ids = self._export_specific_product(obj, template_sku, url, session)
				if mage_ids and mage_ids[0]>0:
					mage_variant_ids.append(mage_ids[1])
		return mage_variant_ids
	
	############# check single attribute lines ########
	def _search_single_values(self, temp_id, attr_id):
		dic = {}
		attr_line_env = self.env['product.attribute.line']
		search_ids  = attr_line_env.search([('product_tmpl_id','=',temp_id),('attribute_id','=',attr_id)])
		if search_ids:
			att_line_obj = search_ids[0]
			if len(att_line_obj.value_ids) == 1:
				dic[att_line_obj.attribute_id.name] = att_line_obj.value_ids.name
		return dic


	############# check attributes lines and set attributes are same ########
	def _check_attribute_with_set(self, set_obj, attribute_line_ids):
		set_attr_ids = set_obj.attribute_ids
		if not set_attr_ids:
			return [-1, str(id)+' Attribute Set Name has no attributes!!!']
		set_attr_list = list(set_attr_ids.ids)
		for attr_id in attribute_line_ids:	
			if attr_id.attribute_id.id not in set_attr_list:
				return [-1, str(id)+' Attribute Set Name not matched with attributes!!!']
		return [1]

	############# check attributes syned return mage attribute ids ########
	def _check_attribute_sync(self, type_obj):
		map_attr_env = self.env['magento.product.attribute']
		mage_attribute_ids = []
		type_search = map_attr_env.search([('name','=',type_obj.attribute_id.id)])
		if type_search:
			mage_attribute_ids.append(type_search[0].mage_id)
		return mage_attribute_ids

	############# fetch product details ########
	def _get_product_array(self, url, session, obj_pro, get_product_data):
		prod_catg = []
		for obj in obj_pro.categ_ids:
			mage_categ_id = self.sync_categories(url, session, obj)
			prod_catg.append(mage_categ_id)
		if obj_pro.categ_id.id:
			mage_categ_id = self.sync_categories(url, session, obj_pro.categ_id)
			prod_catg.append(mage_categ_id)
		status = 2
		if obj_pro.sale_ok:
			status = 1		
		get_product_data['name'] = obj_pro.name
		get_product_data['short_description'] = obj_pro.description_sale or ' '
		get_product_data['description'] = obj_pro.description or ' '
		get_product_data['weight'] = obj_pro.weight or 0.00
		get_product_data['categories'] = prod_catg
		get_product_data['ean'] = obj_pro.barcode		
		get_product_data['status'] = status
		if not get_product_data.has_key('websites'):
			get_product_data['websites'] = [1]
		return get_product_data

	############# create product image ########
	def _product_attribute_media(self, url, session, obj_pro, mage_product_id, opr):
		if obj_pro.image:			
			image_file = {'content':obj_pro.image,'mime':'image/jpeg'}
			if image_file:
				self.server_call(session, url, 'magerpsync.update_product_image', [[mage_product_id, image_file, opr]])
		return True

	#############################################
	##    		Specific product sync	       ##
	#############################################
	def _export_specific_product(self, obj_pro, template_sku, url, session):
		"""
		@param code: product Id.
		@param context: A standard dictionary
		@return: list
		"""
		get_product_data = {}
		map_variant=[]		
		pro_attr_id = 0
		price_extra = 0
		mag_pro_pool = self.env['magento.product']
		if obj_pro:
			sku = obj_pro.default_code or 'Ref %s'%obj_pro.id
			get_product_data['currentsetname'] = ""
			if obj_pro.attribute_value_ids:
				for value_id in obj_pro.attribute_value_ids:
					attrname = str(value_id.attribute_id.name.lower().replace(" ","_").replace("-","_"))	
					valuename = value_id.name
					get_product_data[attrname] = valuename					
					pro_attr_id = value_id.attribute_id.id
					search_price_id = self.env['product.attribute.price'].search([('product_tmpl_id','=',obj_pro.product_tmpl_id.id),('value_id','=',value_id.id)])
					if search_price_id:
						price_extra += search_price_id[0].price_extra

			get_product_data['currentsetname'] = obj_pro.product_tmpl_id.attribute_set_id.name
			if template_sku == "single_variant":
				get_product_data['visibility'] = 4
			else:
				get_product_data['visibility'] = 1
			get_product_data['price'] = obj_pro.list_price+price_extra or 0.00
			get_product_data = self._get_product_array(url, session, obj_pro, get_product_data)
			get_product_data['tax_class_id'] = '0'
			if obj_pro.type in ['product','consu']:
				prodtype = 'simple'
			else:
				prodtype = 'virtual'	
			obj_pro.write({'prod_type':prodtype})
			pro = self.prodcreate(url, session, obj_pro, prodtype, sku, get_product_data)
			if pro and pro[0] != 0:
				self._product_attribute_media(url, session, obj_pro, pro[1], "create")
			return pro

	#############################################
	##    		single products	create 	       ##
	#############################################
	def prodcreate(self, url, session, obj_pro, prodtype, prodsku, put_product_data):
		stock = 0
		quantity = 0
		pro_id = obj_pro.id
		if put_product_data['currentsetname']:
			current_set = put_product_data['currentsetname']
		else:
			currset = self.server_call(session, url, 'product_attribute_set.list')			
			current_set = ""
			if currset[0] > 0:
				current_set = currset[1].get('set_id')
		newprod = [prodtype, current_set, prodsku, put_product_data]
		pro = self.server_call(session, url, 'product.create', newprod)
		if pro[0] > 0:
			oe_product_qty = obj_pro.qty_available
			if oe_product_qty > 0:
				quantity = oe_product_qty
				stock = 1
			self.server_call(session, url, 'product_stock.update', [pro[1] ,{'manage_stock':1,'qty':quantity,'is_in_stock':stock}])
			erp_map_data = {
							'pro_name':pro_id,
							'oe_product_id':pro_id,
							'mag_product_id':pro[1] ,
							'instance_id': self._context.get('instance_id')
							}
			self.env['magento.product'].create(erp_map_data)
			self.server_call(session, url, 'magerpsync.product_map', [{'mage_product_id':pro[1] ,'erp_product_id':pro_id}])
		return  pro

	#############################################
	##    	update specific product template   ##
	#############################################
	def _update_specific_product_template(self, temp_obj, url, session):
		get_product_data = {}
		mage_variant_ids=[]
		mage_price_changes = {}
		obj_pro = temp_obj.template_name
		mage_id = temp_obj.mage_product_id
		if obj_pro and mage_id:
			map_prod_env = self.env['magento.product']
			get_product_data['price'] = obj_pro.list_price or 0.00
			get_product_data = self._get_product_array(url, session, obj_pro, get_product_data)
			if obj_pro.product_variant_ids:
				if temp_obj.is_variants == True and obj_pro.is_product_variant == False:
					if obj_pro.attribute_line_ids :
						for obj in obj_pro.product_variant_ids:
							mage_update_ids = []
							vid = obj.id
							search_ids = map_prod_env.search([('pro_name','=',vid),('instance_id','=',self._context['instance_id'])])
							if search_ids:
								mage_update_ids = self._update_specific_product(search_ids[0], url, session)
				else:
					for obj in obj_pro.product_variant_ids:
						name  = obj_pro.name
						price = obj_pro.list_price or 0.0
						mage_update_ids = []
						vid = obj.id
						search_ids = map_prod_env.search([('pro_name','=',vid),('instance_id','=',self._context['instance_id'])])
						if search_ids:
							mage_update_ids = self._update_specific_product(search_ids[0], url, session)			
						if mage_update_ids and mage_update_ids[0]>0:
							temp_obj.need_sync = 'No'
						return mage_update_ids
				if mage_id:
					check = self._product_attribute_media(url, session, obj_pro, mage_id, 'write')
				
			else:
				return [-1, str(temp_obj.id)+' No Variant Ids Found!!!']
			update_data = [mage_id, get_product_data]
			self.server_call(session, url, 'product.update', update_data)
			temp_obj.need_sync = 'No'
			return [1, obj_pro.id]

	#############################################
	##    		update specific product	       ##
	#############################################
	def _update_specific_product(self, pro_obj, url, session):
		get_product_data = {}
		obj_pro = pro_obj.pro_name
		mage_id = pro_obj.mag_product_id
		if obj_pro and mage_id:
			quantity = 0
			stock = 0
			price_extra=0
			if obj_pro.attribute_value_ids:
				for value_id in obj_pro.attribute_value_ids:
					get_product_data[value_id.attribute_id.name] = value_id.name
					pro_attr_id = value_id.attribute_id.id
					search_price_id = self.env['product.attribute.price'].search([('product_tmpl_id','=',obj_pro.product_tmpl_id.id),('value_id','=',value_id.id)])
					if search_price_id:
						price_extra += search_price_id[0].price_extra
			get_product_data['price'] = obj_pro.list_price+price_extra or 0.00
			get_product_data = self._get_product_array(url, session, obj_pro, get_product_data)
			update_data = [mage_id, get_product_data]
			pro = self.server_call(session, url, 'product.update', update_data)
			if mage_id:
				check = self._product_attribute_media(url, session, obj_pro, mage_id, 'write')
			pro_obj.need_sync = 'No'
			if pro[0] > 0 and obj_pro.qty_available>0:
				quantity = obj_pro.qty_available
				stock = 1
			connection = self.env['magento.configure'].search([('active','=',True),('inventory_sync','=','enable')])
			if connection:
				self.server_call(session, url, 'product_stock.update', [mage_id, {'manage_stock':1, 'qty':quantity,'is_in_stock':stock}])
			return  [1, obj_pro.id]

	def get_mage_region_id(self, url, session, region, country_code):
		""" 
		@return magneto region id 
		"""
		region_obj = self.env['magento.region']
		map_id = region_obj.search([('country_code','=',country_code)])
		if not map_id:
			return_id = self.env['region.wizard']._sync_mage_region(url, session, country_code)			
		region_ids = region_obj.search([('name','=',region),('country_code','=',country_code)])
		if region_ids:
			id = region_ids[0].mag_region_id
			return id
		else:		
			return 0
# END