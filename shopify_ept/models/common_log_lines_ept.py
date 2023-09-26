# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.
from datetime import datetime, timedelta
from odoo import models, fields


class CommonLogLineEpt(models.Model):
    _inherit = "common.log.lines.ept"

    shopify_product_data_queue_line_id = fields.Many2one("shopify.product.data.queue.line.ept",
                                                         "Shopify Product Queue Line")
    shopify_order_data_queue_line_id = fields.Many2one("shopify.order.data.queue.line.ept",
                                                       "Shopify Order Queue Line")
    shopify_customer_data_queue_line_id = fields.Many2one("shopify.customer.data.queue.line.ept",
                                                          "Shopify Customer Queue Line")
    shopify_payout_report_line_id = fields.Many2one("shopify.payout.report.line.ept")
    shopify_export_stock_queue_line_id = fields.Many2one("shopify.export.stock.queue.line.ept",
                                                         "Shopify Export Stock Queue Line")

    def shopify_create_product_log_line(self, message, model_id, queue_line_id, log_book_id, sku=""):
        """
        This method used to create a log line for product mismatch logs.
        @return: log_line
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 22/10/2019.
        @change: Maulik Barad on Date 02-Sep-2020.
        """
        vals = self.shopify_prepare_log_line_vals(message, model_id, queue_line_id, log_book_id)

        vals.update({
            'shopify_product_data_queue_line_id': queue_line_id.id if queue_line_id else False,
            "default_code": sku
        })
        log_line = self.create(vals)
        return log_line

    def shopify_create_order_log_line(self, message, model_id, queue_line_id, log_book_id, order_ref=""):
        """This method used to create a log line for order mismatch logs.
            @param : self, message, model_id, queue_line_id
            @return: log_line
            @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 11/11/2019.
        """
        if order_ref:
            domain = [("message", "=", message), ("model_id", "=", model_id), ("order_ref", "=", order_ref)]
            log_line = self.search(domain)
            if log_line:
                log_line.update({"write_date": datetime.now(), "log_book_id": log_book_id.id if log_book_id else False,
                                 "shopify_order_data_queue_line_id": queue_line_id and queue_line_id.id or False})
                return log_line

        vals = self.shopify_prepare_log_line_vals(message, model_id, queue_line_id, log_book_id)

        vals.update({'shopify_order_data_queue_line_id': queue_line_id and queue_line_id.id or False,
                     "order_ref": order_ref})
        log_line = self.create(vals)
        return log_line

    def shopify_create_customer_log_line(self, message, model_id, queue_line_id, log_book_id):
        """This method used to create a log line for customer mismatch logs.
        """
        vals = self.shopify_prepare_log_line_vals(message, model_id, queue_line_id, log_book_id)
        vals.update({
            'shopify_customer_data_queue_line_id': queue_line_id and queue_line_id.id or False,
        })
        log_line = self.create(vals)
        return log_line

    def shopify_prepare_log_line_vals(self, message, model_id, res_id, log_book_id):
        """ Prepare vals for the log line.
            :param message: Error/log message
            :param model_id: Record of model
            :param res_id: Res Id(Here we can set process record id).
            :param log_book_id: Record of log book.
            @return: vals
            @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 14 October 2020 .
            Task_id: 167537
        """
        vals = {'message': message,
                'model_id': model_id,
                'res_id': res_id.id if res_id else False,
                'log_book_id': log_book_id.id if log_book_id else False,
                }
        return vals

    def create_payout_schedule_activity(self, note, payout_id):
        """
        Using this method Notify to user through the log and schedule activity.
        @author: Maulik Barad on Date 10-Dec-2020.
        """
        if self:
            mail_activity_obj = self.env['mail.activity']
            log_lines = self
            log_book = log_lines.log_book_id

            activity_type_id = log_book.shopify_instance_id.shopify_activity_type_id.id
            date_deadline = datetime.strftime(
                datetime.now() + timedelta(days=int(log_book.shopify_instance_id.shopify_date_deadline)), "%Y-%m-%d")
            model_id = self.get_model_id("shopify.payout.report.ept")
            group_accountant = self.env.ref('account.group_account_user')

            if note:
                for user_id in group_accountant.users:
                    mail_activity = mail_activity_obj.search(
                        [('res_model_id', '=', model_id), ('user_id', '=', user_id.id), ('note', '=', note),
                         ('activity_type_id', '=', activity_type_id)])
                    if mail_activity:
                        continue
                    vals = {'activity_type_id': activity_type_id,
                            'note': note,
                            'res_id': payout_id,
                            'user_id': user_id.id or self._uid,
                            'res_model_id': model_id,
                            'date_deadline': date_deadline}
                    mail_activity_obj.create(vals)

    def shopify_create_export_stock_log_line(self, message, model_id, queue_line_id, log_book_id):
        """
        This method used to create a log line for Export Stock mismatch logs.
        @return: log_line
        @author: Nilam Kubavat @Emipro Technologies Pvt. Ltd on date 29-Aug-2022.
        """
        vals = self.shopify_prepare_log_line_vals(message, model_id, queue_line_id, log_book_id)

        vals.update({
            'shopify_export_stock_queue_line_id': queue_line_id.id if queue_line_id else False
        })
        log_line = self.create(vals)
        return log_line
