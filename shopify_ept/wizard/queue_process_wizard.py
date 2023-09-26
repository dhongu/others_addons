# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.

from odoo import models, _


class ShopifyQueueProcessEpt(models.TransientModel):
    _name = 'shopify.queue.process.ept'
    _description = 'Shopify Queue Process'

    def manual_queue_process(self):
        """
        This method is used to call child methods while manually queue(product, order and customer) process.
        """
        queue_process = self._context.get('queue_process')
        if queue_process == "process_product_queue_manually":
            self.sudo().process_product_queue_manually()
        if queue_process == "process_customer_queue_manually":
            self.sudo().process_customer_queue_manually()
        if queue_process == "process_order_queue_manually":
            self.sudo().process_order_queue_manually()
        if queue_process == "process_export_stock_queue_manually":
            self.sudo().process_export_stock_queue_manually()

    def process_product_queue_manually(self):
        """This method used to process the product queue manually. You can call the method from here :
            Shopify => Processes => Queues Logs => Products => Action => Process Queue Manually.
            @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 25/10/2019.
        """
        model = self._context.get('active_model')
        shopify_product_queue_line_obj = self.env["shopify.product.data.queue.line.ept"]
        product_queue_ids = self._context.get('active_ids')
        if model == 'shopify.product.data.queue.line.ept':
            product_queue_ids = shopify_product_queue_line_obj.search(
                [('id', 'in', product_queue_ids)]).mapped("product_data_queue_id").ids
        for product_queue_id in product_queue_ids:
            product_queue_line_batch = shopify_product_queue_line_obj.search(
                [("product_data_queue_id", "=", product_queue_id),
                 ("state", "in", ('draft', 'failed'))])
            product_queue_line_batch.process_product_queue_line_data()
        return True

    def process_customer_queue_manually(self):
        """
        This method used to process the customer queue manually. You can call the method from here :
        Shopify => Processes => Queues Logs => Customers => Action => Process Queue Manually.
        @author: Angel Patel @Emipro Technologies Pvt. Ltd on date 23/10/2019.
        :Task ID: 157065
        """
        model = self._context.get('active_model')
        customer_queue_line_obj = self.env["shopify.customer.data.queue.line.ept"]
        customer_queue_ids = self._context.get("active_ids")
        if model == "shopify.customer.data.queue.line.ept":
            customer_queue_ids = customer_queue_line_obj.search([('id', 'in', customer_queue_ids)]).mapped(
                "synced_customer_queue_id").ids
        for customer_queue_id in customer_queue_ids:
            synced_customer_queue_line_ids = customer_queue_line_obj.search(
                [("synced_customer_queue_id", "=", customer_queue_id),
                 ("state", "in", ["draft", "failed"])])
            if synced_customer_queue_line_ids:
                synced_customer_queue_line_ids.process_customer_queue_lines()

    def process_order_queue_manually(self):
        """This method used to process the customer queue manually. You can call the method from here :
            Shopify => Processes => Queues Logs => Orders => Action => Process Queue Manually.
            @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 14/10/2019.
        """
        model = self._context.get('active_model')
        shopify_order_queue_line_obj = self.env["shopify.order.data.queue.line.ept"]
        order_queue_ids = self._context.get('active_ids')
        if model == "shopify.order.data.queue.line.ept":
            order_queue_ids = shopify_order_queue_line_obj.search([('id', 'in', order_queue_ids)]).mapped(
                "shopify_order_data_queue_id").ids
        self.env.cr.execute(
            """update shopify_order_data_queue_ept set is_process_queue = False where is_process_queue = True""")
        self._cr.commit()
        for order_queue_id in order_queue_ids:
            order_queue_line_batch = shopify_order_queue_line_obj.search(
                [("shopify_order_data_queue_id", "=", order_queue_id),
                 ("state", "in", ('draft', 'failed'))])
            order_queue_line_batch.process_import_order_queue_data()
        return True

    def process_export_stock_queue_manually(self):
        """
        This method used to process the export stock queue manually.
        @author: Nilam Kubavat @Emipro Technologies Pvt.Ltd on date 31-Aug-2022.
        Task Id : 199065
        """
        model = self._context.get('active_model')
        shopify_export_stock_queue_line_obj = self.env["shopify.export.stock.queue.line.ept"]
        export_stock_queue_ids = self._context.get('active_ids')
        if model == "shopify.export.stock.queue.line.ept":
            export_stock_queue_ids = shopify_export_stock_queue_line_obj.search([('id', 'in', export_stock_queue_ids)]).mapped(
                "export_stock_queue_id").ids
        self.env.cr.execute(
            """update shopify_export_stock_queue_ept set is_process_queue = False where is_process_queue = True""")
        self._cr.commit()
        for export_stock_queue_id in export_stock_queue_ids:
            export_stock_queue_line_obj = shopify_export_stock_queue_line_obj.search(
                [("export_stock_queue_id", "=", export_stock_queue_id),
                 ("state", "in", ('draft', 'failed'))])
            export_stock_queue_line_obj.process_export_stock_queue_data()
        return True

    def set_to_completed_queue(self):
        """
        This method used to change the queue(order, product and customer) state as completed.
        Haresh Mori on date 25/Dec/2019
        """
        queue_process = self._context.get('queue_process')
        if queue_process == "set_to_completed_order_queue":
            self.set_to_completed_order_queue_manually()
        if queue_process == "set_to_completed_product_queue":
            self.set_to_completed_product_queue_manually()
        if queue_process == "set_to_completed_customer_queue":
            self.set_to_completed_customer_queue_manually()
        if queue_process == "set_to_completed_export_stock_queue":
            self.set_to_completed_export_stock_queue_manually()

    def set_to_completed_order_queue_manually(self):
        """This method used to set order queue as completed. You can call the method from here :
            Shopify => Processes => Queues Logs => Orders => SET TO COMPLETED.
            @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 25/12/2019.
        """
        order_queue_ids = self._context.get('active_ids')
        order_queue_ids = self.env['shopify.order.data.queue.ept'].browse(order_queue_ids)
        for order_queue_id in order_queue_ids:
            queue_lines = order_queue_id.order_data_queue_line_ids.filtered(
                lambda line: line.state in ['draft', 'failed'])
            queue_lines.write({'state': 'cancel'})
            order_queue_id.message_post(
                body=_("Manually set to cancel queue lines %s - ") % (queue_lines.mapped('shopify_order_id')))
        return True

    def set_to_completed_product_queue_manually(self):
        """This method used to set product queue as completed. You can call the method from here :
            Shopify => Processes => Queues Logs => Products => SET TO COMPLETED.
            @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 25/12/2019.
        """
        product_queue_ids = self._context.get('active_ids')
        product_queue_ids = self.env['shopify.product.data.queue.ept'].browse(product_queue_ids)
        for product_queue_id in product_queue_ids:
            queue_lines = product_queue_id.product_data_queue_lines.filtered(
                lambda line: line.state in ['draft', 'failed'])
            queue_lines.write({'state': 'cancel', 'shopify_image_import_state': 'done'})
            product_queue_id.message_post(
                body=_("Manually set to cancel queue lines %s - ") % (queue_lines.mapped('product_data_id')))
        return True

    def set_to_completed_customer_queue_manually(self):
        """This method used to set customer queue as completed. You can call the method from here :
            Shopify => Processes => Queues Logs => Customers => SET TO COMPLETED.
            @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 25/12/2019.
        """
        customer_queue_ids = self._context.get('active_ids')
        customer_queue_ids = self.env['shopify.customer.data.queue.ept'].browse(customer_queue_ids)
        for customer_queue_id in customer_queue_ids:
            queue_lines = customer_queue_id.synced_customer_queue_line_ids.filtered(
                lambda line: line.state in ['draft', 'failed'])
            queue_lines.write({'state': 'cancel'})
        return True

    def set_to_completed_export_stock_queue_manually(self):
        """This method used to set export stock queue as completed. You can call the method from here :
            Shopify => Processes => Queues Logs => Export Stock Queues => SET TO COMPLETED.
            @author: Meera Sidapara @Emipro Technologies Pvt. Ltd on date 16/09/2012.
        """
        export_stock_queue_ids = self._context.get('active_ids')
        export_stock_queue_ids = self.env['shopify.export.stock.queue.ept'].browse(export_stock_queue_ids)
        for export_stock_queue_id in export_stock_queue_ids:
            queue_lines = export_stock_queue_id.export_stock_queue_line_ids.filtered(
                lambda line: line.state in ['draft', 'failed'])
            queue_lines.write({'state': 'cancel'})
        return True

    def instance_active_archive(self):
        instances = self.env['shopify.instance.ept'].browse(self._context.get('active_ids'))
        for instance in instances:
            instance.shopify_action_archive_unarchive()
        return True
