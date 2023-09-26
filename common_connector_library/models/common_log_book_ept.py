# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.
from odoo import models, fields, api


class CommonLogBookEpt(models.Model):
    _name = "common.log.book.ept"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = 'id desc'
    _description = "Common log book Ept"

    name = fields.Char(readonly=True)
    type = fields.Selection([('import', 'Import'), ('export', 'Export')], string="Operation")
    module = fields.Selection([('amazon_ept', 'Amazon Connector'),
                               ('woocommerce_ept', 'Woocommerce Connector'),
                               ('shopify_ept', 'Shopify Connector'),
                               ('magento_ept', 'Magento Connector'),
                               ('bol_ept', 'Bol Connector'),
                               ('ebay_ept', 'Ebay Connector'),
                               ('amz_vendor_central', 'Amazon Vendor Central')])
    active = fields.Boolean(default=True)
    log_lines = fields.One2many('common.log.lines.ept', 'log_book_id')
    message = fields.Text()
    model_id = fields.Many2one("ir.model", help="Model Id", string="Model")
    res_id = fields.Integer(string="Record ID", help="Process record id")
    attachment_id = fields.Many2one('ir.attachment', string="Attachment")
    file_name = fields.Char()
    sale_order_id = fields.Many2one(comodel_name='sale.order', string='Sale Order')

    @api.model
    def create(self, vals):
        """ To generate a sequence for a common logbook.
            @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 23 September 2021 .
            Task_id: 178058
        """
        seq = self.env['ir.sequence'].next_by_code('common.log.book.ept') or '/'
        vals['name'] = seq
        return super(CommonLogBookEpt, self).create(vals)

    def create_common_log_book(self, process_type, instance_field, instance, model_id, module):
        """ This method used to create a log book record.
            @param process_type: Generally, the process type value is 'import' or 'export'.
            @param : Name of the field which relates to the instance field for different apps.
            @param instance: Record of instance.
            @param model_id: Model related to log, like create a sales order related log then pass the sales order
            model.
            @param module: For which App this log book is belongs to.
            @return: Record of log book.
            @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 23 September 2021 .
            Task_id:
        """
        log_book_id = self.create({"type": process_type,
                                   "module": module,
                                   instance_field: instance.id,
                                   "model_id": model_id,
                                   "active": True})
        return log_book_id

    def create_common_log_book_ept(self, **kwargs):
        values = {}
        for key, value in kwargs.items():
            if hasattr(self, key):
                values.update({key: value})
        if kwargs.get('model_name'):
            model = self._get_model_id(kwargs.get('model_name'))
            values.update({'model_id': model.id})
        return self.create(values)

    def _get_model_id(self, model_name):
        model_id = self.env['ir.model']
        return model_id.search([('model', '=', model_name)])
