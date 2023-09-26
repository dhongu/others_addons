# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.
from odoo import models, fields, api


class CommonLogLineEpt(models.Model):
    _name = "common.log.lines.ept"
    _description = "Common log line"

    product_id = fields.Many2one('product.product', 'Product')
    order_ref = fields.Char('Order Reference')
    default_code = fields.Char('SKU')
    log_book_id = fields.Many2one('common.log.book.ept', ondelete="cascade")
    message = fields.Text()
    model_id = fields.Many2one("ir.model", string="Model")
    res_id = fields.Integer("Record ID")
    mismatch_details = fields.Boolean(string='Mismatch Detail', help="Mismatch Detail of process order")
    file_name = fields.Char()
    sale_order_id = fields.Many2one(comodel_name='sale.order', string='Sale Order')
    log_line_type = fields.Selection(selection=[('success', 'Success'), ('fail', 'Fail')],default='fail')

    @api.model
    def get_model_id(self, model_name):
        """ Used to get model id.
            @param model_name: Name of model, like sale.order
            @return: It will return record of model.
            @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 23 September 2021 .
            Task_id: 178058
        """
        model = self.env['ir.model'].search([('model', '=', model_name)])
        if model:
            return model.id
        return False

    def create_log_lines(self, message, model_id, res_id, log_book_id, default_code='', order_ref='', product_id=False):
        """ Used to create a log lines.
            @param message: Error message
            @param model_id: Record of model
            @param res_id: Res Id(Here we can set process record id).
            @param log_book_id: Record of log book id.
            @param default_code: Default code of product if product process log
            @param order_ref: Order reference if order process log
            @param product_id: Record of product variant.
            @return: Record of log line.
            @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 23 September 2021 .
            Task_id: 178058
        """
        vals = {'message': message,
                'model_id': model_id,
                'res_id': res_id.id if res_id else False,
                'log_book_id': log_book_id.id if log_book_id else False,
                'default_code': default_code,
                'order_ref': order_ref,
                'product_id': product_id
                }
        log_line = self.create(vals)
        return log_line

    def create_common_log_line_ept(self, **kwargs):
        values = {}
        for key, value in kwargs.items():
            if hasattr(self, key):
                values.update({key: value})
        if kwargs.get('model_name'):
            model_id = self.log_book_id._get_model_id(kwargs.get('model_name'))
            values.update({'model_id': model_id.id})
        return self.create(values)
