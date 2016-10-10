# -*- coding: utf-8 -*-
#################################################################################
#
#    Copyright (c) 2015-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
#
#################################################################################

import xmlrpclib
from openerp.exceptions import UserError
from openerp import api, fields, models
	
	######################## Mapping update Model(Used from server action) #########################
	
class MappingUpdate(models.TransientModel):
	_name = "mapping.update"

	need_sync = fields.Selection([('Yes', 'Yes'),('No', 'No')], string='Update Required')
	
	@api.model
	def open_update_wizard(self):
		partial = self.create({})
		return { 'name': ("Bulk Action"),
				 'view_mode': 'form',
				 'view_id': False,
				 'view_type': 'form',
				'res_model': 'mapping.update',
				 'res_id': partial.id,
				 'type': 'ir.actions.act_window',
				 'nodestroy': True,
				 'target': 'new',
				 'context':self._context,
				 'domain': '[]',
			}

	@api.multi
	def update_mapping_status(self):
		count = 0
		model = self._context.get('active_model')
		active_ids = self._context.get('active_ids')
		status = self.need_sync
		for i in active_ids:
			self.env[model].browse(i).need_sync = status
			count = count+1
		text = 'Status of %s record has been successfully updated to %s.'%(count,status)
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