# -*- coding: utf-8 -*-
#################################################################################
#
#    Copyright (c) 2015-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
#
#################################################################################

import xmlrpclib
from openerp.exceptions import UserError
from openerp import api, fields, models

class SynchronizationWizard(models.TransientModel):
	_name = 'synchronization.wizard'

	action = fields.Selection([('export','Export'),('update','Update')], string='Action', default= "export", required=True, help="""Export: Export all Odoo Category/Products at Magento. Update: Update all synced products/categories at magento, which requires to be update at magento""")
	
	
	@api.multi
	def start_category_synchronization(self):
		ctx = dict(self._context or {})
		ctx['sync_opr'] = self.action
		message = self.env['magento.synchronization'].with_context(ctx).export_categories_check()
		return message

	@api.multi
	def start_product_synchronization(self):
		ctx = dict(self._context or {})
		ctx['sync_opr'] = self.action
		message = self.env['magento.synchronization'].with_context(ctx).export_product_check()
		return message

	@api.model
	def start_bulk_product_synchronization(self):
		partial = self.create({})
		ctx = dict(self._context or {})
		ctx['check'] = False
		return { 'name': "Synchronization Bulk Product",
				 'view_mode': 'form',
				 'view_id': False,
				 'view_type': 'form',
				'res_model': 'synchronization.wizard',
				 'res_id': partial.id,
				 'type': 'ir.actions.act_window',
				 'nodestroy': True,
				 'target': 'new',
				 'context': ctx,
				 'domain': '[]',
			}

	@api.model
	def start_bulk_category_synchronization(self):
		partial = self.create({})
		ctx = dict(self._context or {})
		ctx['All'] = True
		return { 'name': "Synchronization Bulk Category",
				 'view_mode': 'form',
				 'view_id': False,
				 'view_type': 'form',
				'res_model': 'synchronization.wizard',
				 'res_id': partial.id,
				 'type': 'ir.actions.act_window',
				 'nodestroy': True,
				 'target': 'new',
				 'context':ctx,
				 'domain': '[]',
			}