import time
import json
import logging
from datetime import datetime
import pytz
from odoo import models, fields, api, _

from ..shopify.pyactiveresource.connection import ResourceNotFound
from ..shopify.pyactiveresource.connection import ClientError
from .. import shopify

utc = pytz.utc

_logger = logging.getLogger("Shopify Export Stock Queue Line")


class ShopifyOrderDataQueueLineEpt(models.Model):
    _name = "shopify.export.stock.queue.line.ept"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = "Shopify Export Stock Queue Line"

    name = fields.Char()
    shopify_instance_id = fields.Many2one("shopify.instance.ept", string="Instance")
    last_process_date = fields.Datetime()
    inventory_item_id = fields.Char()
    location_id = fields.Char()
    quantity = fields.Integer()
    shopify_product_id = fields.Many2one('shopify.product.product.ept', string="Product")
    state = fields.Selection([("draft", "Draft"), ("failed", "Failed"), ("done", "Done"),
                              ("cancel", "Cancelled")],
                             default="draft")
    export_stock_queue_id = fields.Many2one("shopify.export.stock.queue.ept", required=True,
                                            ondelete="cascade", copy=False)
    common_log_lines_ids = fields.One2many("common.log.lines.ept",
                                           "shopify_export_stock_queue_line_id",
                                           help="Log lines created against which line.")

    def auto_export_stock_queue_data(self):
        """
        This method is used to find export stock queue which queue lines have state in draft and is_action_require is False.
        @author: Nilam Kubavat @Emipro Technologies Pvt.Ltd on date 31-Aug-2022.
        Task Id : 199065
        """
        export_stock_queue_obj = self.env["shopify.export.stock.queue.ept"]
        export_stock_queue_ids = []

        self.env.cr.execute(
            """update shopify_export_stock_queue_ept set is_process_queue = False where is_process_queue = True""")
        self._cr.commit()

        query = """select distinct queue.id
                           from shopify_export_stock_queue_line_ept as queue_line
                           inner join shopify_export_stock_queue_ept as queue on queue_line.export_stock_queue_id = queue.id
                           where queue_line.state in ('draft') and queue.is_action_require = 'False'
                           GROUP BY queue.id
                           ORDER BY queue.id;
           """
        self._cr.execute(query)
        export_stock_queue_list = self._cr.fetchall()
        if not export_stock_queue_list:
            return True

        for result in export_stock_queue_list:
            if result[0] not in export_stock_queue_ids:
                export_stock_queue_ids.append(result[0])

        queues = export_stock_queue_obj.browse(export_stock_queue_ids)
        self.filter_export_stock_queue_lines_and_post_message(queues)

    def filter_export_stock_queue_lines_and_post_message(self, queues):
        """
        This method is used to post a message if the queue is process more than 3 times otherwise
        it calls the child method to process the export stock queue line.
        @author: Nilam Kubavat @Emipro Technologies Pvt.Ltd on date 31-Aug-2022.
        Task Id : 199065
        """
        ir_model_obj = self.env["ir.model"]
        common_log_book_obj = self.env["common.log.book.ept"]
        start = time.time()
        export_stock_queue_process_cron_time = queues.shopify_instance_id.get_shopify_cron_execution_time(
            "shopify_ept.process_shopify_export_stock_queue")

        for queue in queues:
            export_stock_queue_line_ids = queue.export_stock_queue_line_ids.filtered(lambda x: x.state == "draft")

            # For counting the queue crashes and creating schedule activity for the queue.
            queue.queue_process_count += 1
            if queue.queue_process_count > 3:
                queue.is_action_require = True
                note = "<p>Need to process this export stock queue manually.There are 3 attempts been made by " \
                       "automated action to process this queue,<br/>- Ignore, if this queue is already processed.</p>"
                queue.message_post(body=note)
                if queue.shopify_instance_id.is_shopify_create_schedule:
                    model_id = ir_model_obj.search([("model", "=", "shopify.export.stock.queue.ept")]).id
                    common_log_book_obj.create_crash_queue_schedule_activity(queue, model_id, note)
                continue

            self._cr.commit()
            export_stock_queue_line_ids.process_export_stock_queue_data()
            if time.time() - start > export_stock_queue_process_cron_time - 60:
                return True

    def process_export_stock_queue_data(self):
        """
        This method is used to processes export stock queue lines.
        @author: Nilam Kubavat @Emipro Technologies Pvt.Ltd on date 31-Aug-2022.
        Task Id : 199065
        """
        common_log_book_obj = self.env["common.log.book.ept"]
        common_log_line_obj = self.env['common.log.lines.ept']
        model_id = common_log_book_obj.log_lines.get_model_id("shopify.export.stock.queue.ept")
        queue_id = self.export_stock_queue_id if len(self.export_stock_queue_id) == 1 else False
        if queue_id:
            instance = queue_id.shopify_instance_id
            instance.connect_in_shopify()
            if queue_id.common_log_book_id:
                log_book_id = queue_id.common_log_book_id
            else:
                log_book_id = common_log_book_obj.shopify_create_common_log_book("export", instance, model_id)
                queue_id.write({'common_log_book_id': log_book_id})
            self.env.cr.execute(
                """update shopify_export_stock_queue_ept set is_process_queue = False where is_process_queue = True""")
            self._cr.commit()
            for queue_line in self:
                log_line = False
                shopify_product = queue_line.shopify_product_id
                odoo_product = shopify_product.product_id
                try:
                    shopify.InventoryLevel.set(queue_line.location_id, queue_line.inventory_item_id,
                                               queue_line.quantity)
                except ClientError as error:
                    if hasattr(error,
                               "response") and error.response.code == 429 and error.response.msg == "Too Many Requests":
                        time.sleep(int(float(error.response.headers.get('Retry-After', 5))))
                        shopify.InventoryLevel.set(queue_line.location_id,
                                                   queue_line.inventory_item_id,
                                                   queue_line.quantity)
                        continue
                    elif error.response.code == 422 and error.response.msg == "Unprocessable Entity":
                        if json.loads(error.response.body.decode()).get("errors")[
                            0] == 'Inventory item does not have inventory tracking enabled':
                            queue_line.shopify_product_id.write({'inventory_management': "Dont track Inventory"})
                            queue_line.write({'state': 'done'})
                        continue
                    elif hasattr(error, "response"):
                        message = "Error while Export stock for Product ID: %s & Product Name: '%s' for instance:" \
                                  "'%s'not found in Shopify store\nError: %s\n%s" % (
                                      odoo_product.id, odoo_product.name, instance.name,
                                      str(error.response.code) + " " + error.response.msg,
                                      json.loads(error.response.body.decode()).get("errors")[0]
                                  )
                        log_line = common_log_line_obj.shopify_create_export_stock_log_line(message, model_id,
                                                                                            queue_line,
                                                                                            log_book_id)
                        queue_line.write({"state": "failed"})
                        continue
                except Exception as error:
                    message = "Error while Export stock for Product ID: %s & Product Name: '%s' for instance: " \
                              "'%s'\nError: %s" % (odoo_product.id, odoo_product.name, instance.name, str(error))
                    log_line = common_log_line_obj.shopify_create_export_stock_log_line(message, model_id, queue_line,
                                                                                        log_book_id)
                    queue_line.write({"state": "failed"})
                    continue
                if not log_line:
                    queue_id.is_process_queue = True
                    queue_line.write({"state": "done"})
                else:
                    queue_line.write({"state": "failed"})
            if not log_book_id.log_lines:
                log_book_id.unlink()
        return True
