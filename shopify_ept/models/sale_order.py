# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.

import json
import logging
from datetime import datetime, timedelta
import time
import pytz

from dateutil import parser

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from ..shopify.pyactiveresource.util import xml_to_dict
from .. import shopify
from ..shopify.pyactiveresource.connection import ClientError

utc = pytz.utc

_logger = logging.getLogger("Shopify Order")


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _get_shopify_order_status(self):
        """
        Set updated_in_shopify of order from the pickings.
        @author: Maulik Barad on Date 06-05-2020.
        """
        for order in self:
            if order.shopify_instance_id:
                pickings = order.picking_ids.filtered(lambda x: x.state != "cancel")
                if pickings:
                    outgoing_picking = pickings.filtered(
                        lambda x: x.location_dest_id.usage == "customer")
                    if all(outgoing_picking.mapped("updated_in_shopify")):
                        order.updated_in_shopify = True
                        continue
                if order.state != 'draft' and order.moves_count > 0:
                    move_ids = self.env["stock.move"].search([("picking_id", "=", False),
                                                              ("sale_line_id", "in", order.order_line.ids)])
                    state = set(move_ids.mapped('state'))
                    if len(set(state)) == 1 and 'done' in set(state):
                        order.updated_in_shopify = True
                        continue
                order.updated_in_shopify = False
                continue
            order.updated_in_shopify = False

    def _search_shopify_order_ids(self, operator, value):
        query = """select so.id from stock_picking sp
                    inner join sale_order so on so.procurement_group_id=sp.group_id                   
                    inner join stock_location on stock_location.id=sp.location_dest_id and stock_location.usage='customer'
                    where sp.updated_in_shopify %s true and sp.state != 'cancel'
                """ % (operator)
        if operator == '=':
            query += """union all
                    select so.id from sale_order as so
                    inner join sale_order_line as sl on sl.order_id = so.id
                    inner join stock_move as sm on sm.sale_line_id = sl.id
                    where sm.picking_id is NULL and sm.state = 'done' and so.shopify_instance_id notnull"""
        self._cr.execute(query)
        results = self._cr.fetchall()
        order_ids = []
        for result_tuple in results:
            order_ids.append(result_tuple[0])
        order_ids = list(set(order_ids))
        return [('id', 'in', order_ids)]

    shopify_order_id = fields.Char("Shopify Order Ref", copy=False)
    shopify_order_number = fields.Char(copy=False)
    shopify_instance_id = fields.Many2one("shopify.instance.ept", "Shopify Instance", copy=False)
    shopify_order_status = fields.Char(copy=False, tracking=True,
                                       help="Shopify order status when order imported in odoo at the moment order"
                                            "status in Shopify.")
    shopify_payment_gateway_id = fields.Many2one('shopify.payment.gateway.ept',
                                                 string="Payment Gateway", copy=False)
    risk_ids = fields.One2many("shopify.order.risk", 'odoo_order_id', "Risks", copy=False)
    shopify_location_id = fields.Many2one("shopify.location.ept", "Shopify Location", copy=False)
    checkout_id = fields.Char(copy=False)
    is_risky_order = fields.Boolean("Risky Order?", default=False, copy=False)
    updated_in_shopify = fields.Boolean("Updated In Shopify ?", compute=_get_shopify_order_status,
                                        search='_search_shopify_order_ids')
    closed_at_ept = fields.Datetime("Closed At", copy=False)
    canceled_in_shopify = fields.Boolean(default=False, copy=False)
    is_pos_order = fields.Boolean("POS Order ?", copy=False, default=False)
    is_service_tracking_updated = fields.Boolean("Service Tracking Updated", default=False, copy=False)
    is_shopify_multi_payment = fields.Boolean("Multi Payments?", default=False, copy=False,
                                              help="It is used to identify that order has multi-payment gateway or not")
    shopify_payment_ids = fields.One2many('shopify.order.payment.ept', 'order_id',
                                          string="Payment Lines")

    _sql_constraints = [('unique_shopify_order',
                         'unique(shopify_instance_id,shopify_order_id,shopify_order_number)',
                         "Shopify order must be Unique.")]

    def create_shopify_log_line(self, message, queue_line, log_book, order_name):
        """
        Creates log line with the message and makes the queue line fail, if queue line is passed.
        @author: Maulik Barad on Date 11-Sep-2020.
        """
        common_log_line_obj = self.env["common.log.lines.ept"]

        common_log_line_obj.shopify_create_order_log_line(message, log_book.model_id.id, queue_line, log_book,
                                                          order_name)
        if queue_line:
            queue_line.write({"state": "failed", "processed_at": datetime.now()})

    def prepare_shopify_customer_and_addresses(self, order_response, pos_order, instance, order_data_line, log_book):
        """
        Searches for existing customer in Odoo and creates in odoo, if not found.
        @author: Maulik Barad on Date 11-Sep-2020.
        """
        res_partner_obj = self.env["res.partner"]
        shopify_res_partner_obj = self.env["shopify.res.partner.ept"]
        message = False

        if pos_order:
            if order_response.get("customer"):
                partner = res_partner_obj.create_shopify_pos_customer(order_response, instance)
            else:
                partner = instance.shopify_default_pos_customer_id
            if not partner:
                message = "Default POS Customer is not set.\nPlease set Default POS Customer in " \
                          "Shopify Configuration."
        else:
            if not any([order_response.get("customer", {}), order_response.get("billing_address", {}),
                        order_response.get("shipping_address", {})]):
                message = "Customer details are not available in %s Order." % (order_response.get("order_number"))
            else:
                partner = order_response.get("customer") and shopify_res_partner_obj.shopify_create_contact_partner(
                    order_response.get("customer"), instance, False, log_book)
        if message:
            self.create_shopify_log_line(message, order_data_line, log_book, order_response.get("name"))
            _logger.info(message)
            return False, False, False

        if not partner:
            if order_data_line:
                order_data_line.write({"state": "failed", "processed_at": datetime.now()})
            return False, False, False

        if partner.parent_id:
            partner = partner.parent_id

        invoice_address = order_response.get("billing_address") and \
                          shopify_res_partner_obj.shopify_create_or_update_address(
                              order_response.get("billing_address"), partner, "invoice") or partner

        delivery_address = order_response.get("shipping_address") and \
                           shopify_res_partner_obj.shopify_create_or_update_address(
                               order_response.get("shipping_address"), partner, "delivery") or partner

        # Below condition as per the task 169257.
        if not partner and invoice_address and delivery_address:
            partner = invoice_address
        if not partner and not delivery_address and invoice_address:
            partner = invoice_address
            delivery_address = invoice_address
        if not partner and not invoice_address and delivery_address:
            partner = delivery_address
            invoice_address = delivery_address

        return partner, delivery_address, invoice_address

    def set_shopify_location_and_warehouse(self, order_response, instance, pos_order):
        """
        This method sets shopify location and warehouse related to that location in order.
        @author: Maulik Barad on Date 11-Sep-2020.
        """
        shopify_location = shopify_location_obj = self.env["shopify.location.ept"]
        if order_response.get("location_id"):
            shopify_location_id = order_response.get("location_id")
        elif order_response.get("fulfillments"):
            shopify_location_id = order_response.get("fulfillments")[0].get("location_id")
        else:
            shopify_location_id = False

        if shopify_location_id:
            shopify_location = shopify_location_obj.search(
                [("shopify_location_id", "=", shopify_location_id),
                 ("instance_id", "=", instance.id)],
                limit=1)

        if shopify_location and shopify_location.warehouse_for_order:
            warehouse_id = shopify_location.warehouse_for_order.id
        else:
            warehouse_id = instance.shopify_warehouse_id.id

        return {"shopify_location_id": shopify_location and shopify_location.id or False,
                "warehouse_id": warehouse_id, "is_pos_order": pos_order}

    def create_shopify_order_lines(self, lines, order_response, instance):
        """
        This method creates sale order line and discount line for Shopify order.
        @author: Maulik Barad on Date 11-Sep-2020.
        """
        total_discount = order_response.get("total_discounts", 0.0)
        order_number = order_response.get("order_number")
        for line in lines:
            is_custom_line, is_gift_card_line, product = self.search_custom_tip_gift_card_product(line, instance)
            price = line.get("price")
            if instance.order_visible_currency:
                price = self.get_price_based_on_customer_visible_currency(line.get("price_set"), order_response, price)
            order_line = self.shopify_create_sale_order_line(line, product, line.get("quantity"),
                                                             product.name, price,
                                                             order_response)
            if is_gift_card_line:
                line_vals = {'is_gift_card_line': True}
                if line.get('name'):
                    line_vals.update({'name': line.get('name')})
                order_line.write(line_vals)

            if is_custom_line:
                order_line.write({'name': line.get('name')})

            if line.get('duties'):
                self.create_shopify_duties_lines(line.get('duties'), order_response, instance)

            if float(total_discount) > 0.0:
                discount_amount = 0.0
                for discount_allocation in line.get("discount_allocations"):
                    if instance.order_visible_currency:
                        discount_total_price = self.get_price_based_on_customer_visible_currency(
                            discount_allocation.get("amount_set"), order_response, discount_amount)
                        if discount_total_price:
                            discount_amount += float(discount_total_price)
                    else:
                        discount_amount += float(discount_allocation.get("amount"))

                if discount_amount > 0.0:
                    _logger.info("Creating discount line for Odoo order(%s) and Shopify order is (%s)", self.name,
                                 order_number)
                    self.shopify_create_sale_order_line({}, instance.discount_product_id, 1,
                                                        product.name, float(discount_amount) * -1,
                                                        order_response, previous_line=order_line,
                                                        is_discount=True)
                    _logger.info("Created discount line for Odoo order(%s) and Shopify order is (%s)", self.name,
                                 order_number)

    def get_price_based_on_customer_visible_currency(self, price_set, order_response, price):
        """
        This method is used to set price based on customer visible currency.
        @author: Meera Sidapara on Date 16-June-2022.
        Task: 193010 - Shopify Multi currency changes
        """
        if float(price_set['shop_money']['amount']) > 0.0 and price_set['shop_money'][
            'currency_code'] == order_response.get('presentment_currency'):
            price = price_set['shop_money']['amount']
        elif float(price_set['presentment_money']['amount']) > 0.0 and price_set['presentment_money'][
            'currency_code'] == order_response.get('presentment_currency'):
            price = price_set['presentment_money']['amount']
        return float(price)

    def create_shopify_duties_lines(self, duties_line, order_response, instance):
        """
        Creates duties lines for shopify orders.
        @author: Meera Sidapara on Date 17-June-2022.
        """
        order_number = order_response.get("order_number")
        product = instance.duties_product_id if instance.duties_product_id else False
        # add duties
        for duties in duties_line:
            duties_amount = 0.0
            if instance.order_visible_currency:
                duties_amount = self.get_price_based_on_customer_visible_currency(duties.get("price_set"),
                                                                                  order_response,
                                                                                  duties_amount)

            if float(duties_amount) > 0.0:
                _logger.info("Creating duties line for Odoo order(%s) and Shopify order is (%s)", self.name,
                             order_number)
                self.shopify_create_sale_order_line(duties, instance.duties_product_id, 1,
                                                    product.name, float(duties_amount),
                                                    order_response, is_duties=True)
                _logger.info("Created duties line for Odoo order(%s) and Shopify order is (%s)", self.name,
                             order_number)

    def search_custom_tip_gift_card_product(self, line, instance):
        """
        Search the products of the custom option, Tip, and Gift card product..
        @author: Haresh Mori on Date 12-June-2021.
        Task: 172889 - TIP order import
        """
        is_custom_line = False
        is_gift_card_line = False
        product = False
        if not line.get('product_id'):
            if line.get('sku'):
                product = self.env["product.product"].search([("default_code", "=", line.get('sku'))], limit=1)
            if not product:
                product = instance.custom_storable_product_id
            is_custom_line = True
        if line.get('name') == 'Tip':
            product = instance.tip_product_id
            is_custom_line = True
        if line.get('gift_card'):
            product = instance.gift_card_product_id
            is_gift_card_line = True
        else:
            if not is_custom_line:
                shopify_product = self.search_shopify_product_for_order_line(line, instance)
                product = shopify_product.product_id

        return is_custom_line, is_gift_card_line, product

    def create_shopify_shipping_lines(self, order_response, instance):
        """
        Creates shipping lines for shopify orders.
        @author: Maulik Barad on Date 11-Sep-2020.
        """
        delivery_carrier_obj = self.env["delivery.carrier"]
        order_number = order_response.get("order_number")
        for line in order_response.get("shipping_lines", []):
            carrier = delivery_carrier_obj.shopify_search_create_delivery_carrier(line, instance)
            shipping_product = instance.shipping_product_id
            if carrier:
                self.write({"carrier_id": carrier.id})
                shipping_product = carrier.product_id
            # Some order in If shipping carrier is not there and Shipping amount is there then create shipping line.
            # Changes suggested by dipesh sir.
            if shipping_product:
                if float(line.get("price")) > 0.0:
                    shipping_price = line.get("price")
                    if instance.order_visible_currency:
                        shipping_price = self.get_price_based_on_customer_visible_currency(line.get("price_set"),
                                                                                           order_response,
                                                                                           shipping_price)
                    order_line = self.shopify_create_sale_order_line(line, shipping_product, 1,
                                                                     shipping_product.name or line.get("title"),
                                                                     shipping_price,
                                                                     order_response, is_shipping=True)
                discount_amount = 0.0
                for discount_allocation in line.get("discount_allocations"):
                    discount_amount += float(discount_allocation.get("amount"))
                if discount_amount > 0.0:
                    _logger.info("Creating discount line for Odoo order(%s) and Shopify order is (%s)", self.name,
                                 order_number)
                    self.shopify_create_sale_order_line({}, instance.discount_product_id, 1,
                                                        shipping_product.name, float(discount_amount) * -1,
                                                        order_response, previous_line=order_line,
                                                        is_discount=True)
                    _logger.info("Created discount line for Odoo order(%s) and Shopify order is (%s)", self.name,
                                 order_number)

    def import_shopify_orders(self, order_data_lines, log_book):
        """
        This method used to create a sale orders in Odoo.
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 11/11/2019.
        Task Id : 157350
        @change: By Maulik Barad on Date 21-Sep-2020.
        @change: By Meera Sidapara on Date 27-Oct-2021 for Task Id : 179249.
        """
        order_risk_obj = self.env["shopify.order.risk"]
        common_log_line_obj = self.env["common.log.lines.ept"]
        order_ids = []
        commit_count = 0
        instance = log_book.shopify_instance_id

        instance.connect_in_shopify()

        for order_data_line in order_data_lines:
            if commit_count == 5:
                self._cr.commit()
                commit_count = 0
            commit_count += 1
            order_data = order_data_line.order_data
            order_response = json.loads(order_data)

            order_number = order_response.get("order_number")
            shopify_financial_status = order_response.get("financial_status")
            _logger.info("Started processing Shopify order(%s) and order id is(%s)", order_number,
                         order_response.get("id"))

            date_order = self.convert_order_date(order_response)
            if str(instance.import_order_after_date) > date_order:
                message = "Order %s is not imported in Odoo due to configuration mismatch.\n Received order date is " \
                          "%s. \n Please check the order after date in shopify configuration." % (order_number,
                                                                                                  date_order)
                _logger.info(message)
                self.create_shopify_log_line(message, order_data_line, log_book, order_response.get("name"))
                continue

            sale_order = self.search_existing_shopify_order(order_response, instance, order_number)

            if sale_order:
                order_data_line.write({"state": "done", "processed_at": datetime.now(),
                                       "sale_order_id": sale_order.id})
                _logger.info("Done the Process of order Because Shopify Order(%s) is exist in Odoo and Odoo order is("
                             "%s)", order_number, sale_order.name)
                continue

            pos_order = order_response.get("source_name", "") == "pos"
            partner, delivery_address, invoice_address = self.prepare_shopify_customer_and_addresses(
                order_response, pos_order, instance, order_data_line, log_book)
            if not partner:
                continue

            lines = order_response.get("line_items")
            if self.check_mismatch_details(lines, instance, order_number, order_data_line, log_book):
                _logger.info("Mismatch details found in this Shopify Order(%s) and id (%s)", order_number,
                             order_response.get("id"))
                order_data_line.write({"state": "failed", "processed_at": datetime.now()})
                continue

            sale_order = self.shopify_create_order(instance, partner, delivery_address, invoice_address,
                                                   order_data_line, order_response, log_book, lines, order_number)
            if not sale_order:
                message = "Configuration missing in Odoo while importing Shopify Order(%s) and id (%s)" % (
                    order_number, order_response.get("id"))
                _logger.info(message)
                self.create_shopify_log_line(message, order_data_line, log_book, order_response.get("name"))
                continue
            order_ids.append(sale_order.id)

            location_vals = self.set_shopify_location_and_warehouse(order_response, instance, pos_order)

            if instance.is_delivery_multi_warehouse:
                warehouses = sale_order.order_line.filtered(lambda line_item: line_item.warehouse_id_ept).mapped(
                    'warehouse_id_ept')
                if warehouses and len(set(warehouses.ids)) == 1:
                    location_vals.update({"warehouse_id": warehouses.id})

            sale_order.write(location_vals)

            risk_result = shopify.OrderRisk().find(order_id=order_response.get("id"))
            if risk_result:
                order_risk_obj.shopify_create_risk_in_order(risk_result, sale_order)
                risk = sale_order.risk_ids.filtered(lambda x: x.recommendation != "accept")
                if risk:
                    sale_order.is_risky_order = True

            _logger.info("Starting auto workflow process for Odoo order(%s) and Shopify order is (%s)",
                         sale_order.name, order_number)
            message = ""
            try:
                if sale_order.shopify_order_status == "fulfilled":
                    sale_order.auto_workflow_process_id.with_context(
                        log_book_id=log_book.id).shipped_order_workflow_ept(sale_order)
                    if order_data_line and order_data_line.shopify_order_data_queue_id.created_by == "scheduled_action":
                        created_by = 'Scheduled Action'
                    else:
                        created_by = self.env.user.name
                    # Below code add for create partially/fully refund
                    message = self.create_shipped_order_refund(shopify_financial_status, order_response, sale_order,
                                                               created_by)
                elif not sale_order.is_risky_order:
                    if sale_order.shopify_order_status == "partial":
                        sale_order.process_order_fullfield_qty(order_response)
                        sale_order.with_context(log_book_id=log_book.id).process_orders_and_invoices_ept()
                        if order_data_line and order_data_line.shopify_order_data_queue_id.created_by == \
                                "scheduled_action":
                            created_by = 'Scheduled Action'
                        else:
                            created_by = self.env.user.name
                        # Below code add for create partially/fully refund
                        message = self.create_shipped_order_refund(shopify_financial_status, order_response, sale_order,
                                                                   created_by)
                    else:
                        sale_order.with_context(log_book_id=log_book.id).process_orders_and_invoices_ept()
            except Exception as error:
                if order_data_line:
                    order_data_line.write({"state": "failed", "processed_at": datetime.now(),
                                           "sale_order_id": sale_order.id})
                message = "Receive error while process auto invoice workflow, Error is:  (%s)" % (error)
                _logger.info(message)
                self.create_shopify_log_line(message, order_data_line, log_book, order_response.get("name"))
                continue
            _logger.info("Done auto workflow process for Odoo order(%s) and Shopify order is (%s)", sale_order.name,
                         order_number)

            if message:
                model_id = common_log_line_obj.get_model_id(self._name)
                common_log_line_obj.shopify_create_order_log_line(message, model_id,
                                                                  order_data_line, log_book)
                order_data_line.write({'state': 'failed', 'processed_at': datetime.now()})
            else:
                order_data_line.write({"state": "done", "processed_at": datetime.now(),
                                       "sale_order_id": sale_order.id})
            _logger.info("Processed the Odoo Order %s process and Shopify Order (%s)", sale_order.name, order_number)

        return order_ids

    def import_shopify_cancel_order(self, instance, from_date, to_date):
        """ This method is used if Shopify orders imported in odoo and after Shopify store in some orders are canceled
            then this method cancel imported orders and created a log note.
            @param : instance,from_date,to_date
            @return: True
            @author: Meera Sidapara @Emipro Technologies Pvt. Ltd on date 16 March 2022.
            Task_id: 185873
        """
        shopify_order_data_queue_obj = self.env["shopify.order.data.queue.ept"]
        instance.connect_in_shopify()
        order_ids = shopify_order_data_queue_obj.shopify_order_request(instance, from_date, to_date, order_type="any")
        for order in order_ids:
            order_data = order.to_dict()
            if order_data.get('cancel_reason'):
                message = ""
                if order_data.get('cancel_reason') == "customer":
                    message = "Customer changed/canceled Order"
                elif order_data.get('cancel_reason') == "fraud":
                    message = "Fraudulent order"
                elif order_data.get('cancel_reason') == "inventory":
                    message = "Items unavailable"
                elif order_data.get('cancel_reason') == "declined":
                    message = "Payment declined"
                elif order_data.get('cancel_reason') == "other":
                    message = "Other"
                sale_order = self.search_existing_shopify_order(order_data, instance, order_data.get("order_number"))
                if sale_order and sale_order.state != 'cancel':
                    sale_order.write({'canceled_in_shopify': True})
                    sale_order.message_post(
                        body=_("The reason for the order cancellation on this Shopify store is that %s.", message))
                    sale_order.cancel_shopify_order()
        instance.last_cancel_order_import_date = to_date - timedelta(days=2)
        return True

    def create_shipped_order_refund(self, shopify_financial_status, order_response, sale_order, created_by):
        """ This method is used to create partially or fully refund in shopify order.
            @param : self
            @return: message
            @author: Meera Sidapara @Emipro Technologies Pvt. Ltd on date 27 November 2021 .
            Task_id: 179249
        """
        message = ""
        if shopify_financial_status == "refunded" or "partially_refunded" and order_response.get(
                "refunds"):
            is_need_create_refund = False
            for refund in order_response.get('refunds'):
                for transaction in refund.get('transactions'):
                    if transaction.get('kind') == 'refund' and transaction.get('status') == 'success':
                        is_need_create_refund = True

            if is_need_create_refund:
                message = sale_order.create_shopify_partially_refund(order_response.get("refunds"),
                                                                     order_response.get('name'), created_by,
                                                                     shopify_financial_status)
            self.prepare_vals_shopify_multi_payment_refund(order_response.get("refunds"), sale_order)
            # refunded = sale_order.create_shopify_refund(order_response.get("refunds"), total_refund, created_by)
            # if refunded[0] == 0:
            #     message = "- Refund can only be generated if it's related order " \
            #               "invoice is found.\n- For order [%s], system could not find the " \
            #               "related order invoice. " % (order_response.get('name'))
            # elif refunded[0] == 2:
            #     message = "- Refund can only be generated if it's related order " \
            #               "invoice is in 'Post' status.\n- For order [%s], system found " \
            #               "related invoice but it is not in 'Post' status." % (
            #                   order_response.get('name'))
            # elif refunded[0] == 3:
            #     message = "- Partial refund is received from Shopify for order [%s].\n " \
            #               "- System do not process partial refunds.\n" \
            #               "- Either create partial refund manually in Odoo or do full " \
            #               "refund in Shopify." % (order_response.get('name'))
        # elif shopify_financial_status == "partially_refunded" and order_response.get("refunds"):
        #     message = sale_order.create_shopify_partially_refund(order_response.get("refunds"),
        #                                                          order_response.get('name'), created_by)
        # self.prepare_vals_shopify_multi_payment_refund(order_response.get("refunds"), sale_order)
        return message

    def prepare_vals_shopify_multi_payment_refund(self, order_refunds, order):
        """ This method is used to manage multi payment wise remaining refund amount.
            @param : order_refunds,order
            @return: True
            @author: Meera Sidapara @Emipro Technologies Pvt. Ltd on date 15 Feb 2022.
            Task_id: 183797
        """
        for refund in order_refunds:
            for transaction in refund.get('transactions'):
                for payment_record in order.shopify_payment_ids:
                    if payment_record.payment_gateway_id.name == transaction.get('gateway'):
                        total_amount = payment_record.remaining_refund_amount - float(transaction.get('amount'))
                        payment_record.write({'remaining_refund_amount': abs(total_amount)})
        return True

    def search_existing_shopify_order(self, order_response, instance, order_number):
        """ This method is used to search the existing shopify order.
            @param : self
            @return: sale_order
            @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 27 October 2020 .
            Task_id: 167537
        """

        sale_order = self.search([("shopify_order_id", "=", order_response.get("id")),
                                  ("shopify_instance_id", "=", instance.id),
                                  ("shopify_order_number", "=", order_number)])
        if not sale_order:
            sale_order = self.search([("shopify_instance_id", "=", instance.id),
                                      ("client_order_ref", "=", order_response.get("name"))])

        return sale_order

    def check_mismatch_details(self, lines, instance, order_number, order_data_queue_line,
                               log_book_id):
        """This method used to check the mismatch details in the order lines.
            @param : self, lines, instance, order_number, order_data_queue_line
            @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 11/11/2019.
            Task Id : 157350
        """
        shopify_product_template_obj = self.env["shopify.product.template.ept"]
        mismatch = False

        for line in lines:
            shopify_variant = self.search_shopify_variant(line, instance)
            if shopify_variant:
                continue
            # Below lines are used for the search gift card product, Task 169381.
            if line.get('gift_card', False):
                product = instance.gift_card_product_id or False
                if product:
                    continue
                message = "Please upgrade the module and then try to import order(%s).\n Maybe the Gift Card " \
                          "product " \
                          "has been deleted, it will be recreated at the time of module upgrade." % order_number
                self.create_shopify_log_line(message, order_data_queue_line, log_book_id, order_number)
                mismatch = True
                break

            if not shopify_variant:
                line_variant_id = line.get("variant_id", False)
                line_product_id = line.get("product_id", False)
                if line_product_id and line_variant_id:
                    shopify_product_template_obj.shopify_sync_products(False, line_product_id,
                                                                       instance, log_book_id,
                                                                       order_data_queue_line)
                    shopify_variant = self.search_shopify_variant(line, instance)
                    if not shopify_variant:
                        message = "Product [%s][%s] not found for Order %s" % (
                            line.get("sku"), line.get("name"), order_number)
                        self.create_shopify_log_line(message, order_data_queue_line, log_book_id, order_number)
                        mismatch = True
                        break
        return mismatch

    def search_shopify_variant(self, line, instance):
        """ This method is used to search the Shopify variant.
            :param line: Response of order line.
            @return: shopify_variant.
            @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 19 October 2020 .
            Task_id: 167537
        """
        shopify_variant = False
        shopify_product_obj = self.env["shopify.product.product.ept"]
        sku = line.get("sku") or False
        if line.get("variant_id", None):
            shopify_variant = shopify_product_obj.search(
                [("variant_id", "=", line.get("variant_id")),
                 ("shopify_instance_id", "=", instance.id), ('exported_in_shopify', '=', True)])
        if not shopify_variant and sku:
            shopify_variant = shopify_product_obj.search(
                [("default_code", "=", sku),
                 ("shopify_instance_id", "=", instance.id), ('exported_in_shopify', '=', True)])
        return shopify_variant

    def shopify_create_order(self, instance, partner, shipping_address, invoice_address,
                             order_data_queue_line, order_response, log_book_id, lines, order_number):
        """This method used to create a sale order and it's line.
            @param : self, instance, partner, shipping_address, invoice_address,order_data_queue_line, order_response
            @return: order
            @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 12/11/2019.
            Task Id : 157350
            @change : if configuration on for Create delivery fee than going to create order line for delivery fee
            @change by : Nilam Kubavat at 09-Aug-2022 for task id : 197829
        """
        payment_gateway_obj = self.env["shopify.payment.gateway.ept"]
        gateway = order_response.get('gateway') or "no_payment_gateway"
        payment_gateway, workflow, payment_term = \
            payment_gateway_obj.shopify_search_create_gateway_workflow(instance, order_data_queue_line, order_response,
                                                                       log_book_id, gateway)

        if not all([payment_gateway, workflow]):
            return False

        order_vals = self.prepare_shopify_order_vals(instance, partner, shipping_address,
                                                     invoice_address, order_response,
                                                     payment_gateway,
                                                     workflow)
        order_vals.update({'payment_term_id': payment_term and payment_term.id or False})
        if len(order_response.get('payment_gateway_names')) > 1:
            payment_vals = self.prepare_vals_shopify_multi_payment(instance, order_data_queue_line, order_response,
                                                                   log_book_id, payment_gateway, workflow)
            if not payment_vals:
                return False
            order_vals.update({'shopify_payment_ids': payment_vals, 'is_shopify_multi_payment': True})

        order = self.create(order_vals)

        _logger.info("Creating order lines for Odoo order(%s) and Shopify order is (%s).", order.name, order_number)
        order.create_shopify_order_lines(lines, order_response, instance)

        _logger.info("Created order lines for Odoo order(%s) and Shopify order is (%s)", order.name, order_number)

        order.create_shopify_shipping_lines(order_response, instance)
        _logger.info("Created Shipping lines for order (%s).", order.name)

        if instance.is_delivery_fee:
            order.create_shopify_Delivery_Fee_lines(order_response, instance)
            _logger.info("Created Delivery Fee for order (%s).", order.name)

        if instance.is_delivery_multi_warehouse:
            self.set_line_warehouse_based_on_location(order, instance)
        return order

    def set_line_warehouse_based_on_location(self, order, instance):
        """
        This method sets order line warehouse based on Shopify Location.
        @author:Meera Sidapara @Emipro Technologies Pvt. Ltd on date 07 September 2022.
        Task Id : 199989 - Fulfillment location wise order
        """
        shopify_location_obj = self.env['shopify.location.ept']
        shopify_order_id = order.shopify_order_id
        shopify_order = shopify.Order().find(shopify_order_id)
        fulfillment_data = shopify_order.get('fulfillment_orders')
        for data in fulfillment_data:
            shopify_location_id = data.get('assigned_location_id')
            line_item_ids = [str(line.get('line_item_id')) for line in data.get('line_items')]
            order_line = order.order_line.filtered(lambda line_item: line_item.shopify_line_id in line_item_ids)
            line_warehouse_id = shopify_location_obj.search(
                [('shopify_location_id', '=', shopify_location_id)]).warehouse_for_order
            order_line.write(
                {'warehouse_id_ept': line_warehouse_id.id if line_warehouse_id else instance.shopify_warehouse_id.id})
        return True

    def create_shopify_Delivery_Fee_lines(self, order_response, instance):
        """
        Creates Delivery Fee lines for shopify orders.
        @author: Nilam Kubavat @Emipro Technologies Pvt. Ltd on date 09-Aug-2022
        Task Id : 197829
        """
        shipping_product = instance.shipping_product_id
        for line in order_response.get("tax_lines", []):
            if line.get('title') == instance.delivery_fee_name:
                delivery_fee_price = line.get("price")
                if instance.order_visible_currency:
                    delivery_fee_price = self.get_price_based_on_customer_visible_currency(line.get("price_set"),
                                                                                           order_response,
                                                                                           delivery_fee_price)
                order_line = self.shopify_create_sale_order_line(line, shipping_product, 1,
                                                                 line.get('title'),
                                                                 delivery_fee_price,
                                                                 order_response)
                order_line.name = line.get('title')

    def prepare_shopify_order_vals(self, instance, partner, shipping_address,
                                   invoice_address, order_response, payment_gateway,
                                   workflow):
        """
        This method used to Prepare a order vals.
        @param : self, instance, partner, shipping_address,invoice_address, order_response, payment_gateway,workflow
        @return: order_vals
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 13/11/2019.
        Task Id : 157350
        """
        date_order = self.convert_order_date(order_response)
        pricelist_id = self.shopify_set_pricelist(order_response=order_response, instance=instance)

        ordervals = {
            "company_id": instance.shopify_company_id.id if instance.shopify_company_id else False,
            "partner_id": partner.ids[0],
            "partner_invoice_id": invoice_address.ids[0],
            "partner_shipping_id": shipping_address.ids[0],
            "warehouse_id": instance.shopify_warehouse_id.id if instance.shopify_warehouse_id else False,
            "date_order": date_order,
            "state": "draft",
            "pricelist_id": pricelist_id.id if pricelist_id else False,
            "team_id": instance.shopify_section_id.id if instance.shopify_section_id else False,
        }
        ordervals = self.create_sales_order_vals_ept(ordervals)
        order_response_vals = self.prepare_order_vals_from_order_response(order_response, instance, workflow,
                                                                          payment_gateway)
        ordervals.update(order_response_vals)
        if not instance.is_use_default_sequence:
            if instance.shopify_order_prefix:
                name = "%s_%s" % (instance.shopify_order_prefix, order_response.get("name"))
            else:
                name = order_response.get("name")
            ordervals.update({"name": name})
        return ordervals

    def create_or_search_sale_tag(self, tag):
        crm_tag_obj = self.env['crm.tag']
        exists_tag = crm_tag_obj.search([('name', '=ilike', tag)], limit=1)
        if not exists_tag:
            exists_tag = crm_tag_obj.create({'name': tag})
        return exists_tag.id

    def convert_order_date(self, order_response):
        """ This method is used to convert the order date in UTC and formate("%Y-%m-%d %H:%M:%S").
            :param order_response: Order response
            @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 19 October 2020 .
            Task_id: 167537
        """
        if order_response.get("created_at", False):
            order_date = order_response.get("created_at", False)
            date_order = parser.parse(order_date).astimezone(utc).strftime("%Y-%m-%d %H:%M:%S")
        else:
            date_order = time.strftime("%Y-%m-%d %H:%M:%S")
            date_order = str(date_order)

        return date_order

    def prepare_order_vals_from_order_response(self, order_response, instance, workflow, payment_gateway):
        """ This method is used to prepare vals from the order response.
            :param order_response: Response of order.
            :param instance: Record of instance.
            :param workflow: Record of auto invoice workflow.
            :param payment_gateway: Record of payment gateway.
            @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 19 October 2020 .
            Task_id: 167537
            @change : pass tag_ids on vals by Nilam Kubavat for task id : 190111 at 19/05/2022
        """
        shopify_source_id = self.find_or_create_shopify_source(order_response.get('source_name'))
        tags = order_response.get("tags").split(",") if order_response.get("tags") != '' else order_response.get("tags")
        tag_ids = []
        for tag in tags:
            tag_ids.append(self.create_or_search_sale_tag(tag))
        order_vals = {
            "checkout_id": order_response.get("checkout_id"),
            "note": order_response.get("note"),
            "shopify_order_id": order_response.get("id"),
            "shopify_order_number": order_response.get("order_number"),
            "shopify_payment_gateway_id": payment_gateway and payment_gateway.id or False,
            "shopify_instance_id": instance.id,
            "shopify_order_status": order_response.get("fulfillment_status") or "unfulfilled",
            "picking_policy": workflow.picking_policy or False,
            "auto_workflow_process_id": workflow and workflow.id,
            "client_order_ref": order_response.get("name"),
            "analytic_account_id": instance.shopify_analytic_account_id.id if instance.shopify_analytic_account_id else False,
            "source_id": shopify_source_id.id,
            "tag_ids": tag_ids
        }
        return order_vals

    def find_or_create_shopify_source(self, source):
        """
        This method is used to find or create shopify source in utm.source.
        @param source: Shopify order source
        @author: Meera Sidapara @Emipro Technologies Pvt. Ltd on date 19 April 2022.
        Task_id: 187155
        """
        utm_source_obj = self.env['utm.source']
        source_id = utm_source_obj.search([('name', '=ilike', source)], limit=1)
        if not source_id:
            source_id = utm_source_obj.create({'name': source})
        return source_id

    def shopify_set_pricelist(self, instance, order_response):
        """
        Author:Bhavesh Jadav 09/12/2019 for the for set price list based on the order response currency because of if
        order currency different then the erp currency so we need to set proper pricelist for that sale order
        otherwise set pricelist based on instance configurations
        """
        currency_obj = self.env["res.currency"]
        pricelist_obj = self.env["product.pricelist"]
        order_currency = order_response.get(
            "presentment_currency") if instance.order_visible_currency else order_response.get(
            "currency") or False
        if order_currency:
            currency = currency_obj.search([("name", "=", order_currency)])
            if instance.shopify_pricelist_id.currency_id.id == currency.id:
                return instance.shopify_pricelist_id
            if not currency:
                currency = currency_obj.search(
                    [("name", "=", order_currency), ("active", "=", False)])
            if currency:
                currency.write({"active": True})
                pricelist = pricelist_obj.search(
                    [("currency_id", "=", currency.id), ("company_id", "=", instance.shopify_company_id.id)],
                    limit=1)
                if pricelist:
                    return pricelist
                pricelist_vals = {"name": currency.name,
                                  "currency_id": currency.id,
                                  "company_id": instance.shopify_company_id.id}
                pricelist = pricelist_obj.create(pricelist_vals)
                return pricelist
            pricelist = pricelist_obj.search([("currency_id", "=", currency.id)], limit=1)
            return pricelist
        pricelist = instance.shopify_pricelist_id if instance.shopify_pricelist_id else False
        return pricelist

    def search_shopify_product_for_order_line(self, line, instance):
        """This method used to search shopify product for order line.
            @param : self, line, instance
            @return: shopify_product
            @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 14/11/2019.
            Task Id : 157350
        """
        shopify_product_obj = self.env["shopify.product.product.ept"]
        variant_id = line.get("variant_id")
        shopify_product = shopify_product_obj.search(
            [("shopify_instance_id", "=", instance.id), ("variant_id", "=", variant_id),
             ('exported_in_shopify', '=', True)], limit=1)
        if not shopify_product:
            shopify_product = shopify_product_obj.search([("shopify_instance_id", "=", instance.id),
                                                          ("default_code", "=", line.get("sku")),
                                                          ('exported_in_shopify', '=', True)], limit=1)
            shopify_product.write({"variant_id": variant_id})
        return shopify_product

    def shopify_create_sale_order_line(self, line, product, quantity, product_name, price,
                                       order_response, is_shipping=False, previous_line=False,
                                       is_discount=False, is_duties=False):
        """
        This method used to create a sale order line.
        @param : self, line, product, quantity,product_name, order_id,price, is_shipping=False
        @return: order_line_id
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 14/11/2019.
        Task Id : 157350
        """
        sale_order_line_obj = self.env["sale.order.line"]
        instance = self.shopify_instance_id
        line_vals = self.prepare_vals_for_sale_order_line(product, product_name, price, quantity)
        order_line_vals = sale_order_line_obj.create_sale_order_line_ept(line_vals)
        order_line_vals = self.shopify_set_tax_in_sale_order_line(instance, line, order_response, is_shipping,
                                                                  is_discount, previous_line, order_line_vals,
                                                                  is_duties)
        if is_discount:
            order_line_vals["name"] = "Discount for " + str(product_name)
            if instance.apply_tax_in_order == "odoo_tax" and previous_line:
                order_line_vals["tax_id"] = previous_line.tax_id

        if is_duties:
            order_line_vals["name"] = "Duties for " + str(product_name)
            if instance.apply_tax_in_order == "odoo_tax" and previous_line:
                order_line_vals["tax_id"] = previous_line.tax_id

        shopify_analytic_tag_ids = instance.shopify_analytic_tag_ids.ids
        order_line_vals.update({
            "shopify_line_id": line.get("id"),
            "is_delivery": is_shipping,
            "analytic_tag_ids": [(6, 0, shopify_analytic_tag_ids)],
        })
        order_line = sale_order_line_obj.create(order_line_vals)
        order_line.with_context(round=False)._compute_amount()
        return order_line

    def prepare_vals_for_sale_order_line(self, product, product_name, price, quantity):
        """ This method is used to prepare a vals to create a sale order line.
            @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 19 October 2020 .
        """
        uom_id = product and product.uom_id and product.uom_id.id or False
        line_vals = {
            "product_id": product and product.ids[0] or False,
            "order_id": self.id,
            "company_id": self.company_id.id,
            "product_uom": uom_id,
            "name": product_name,
            "price_unit": price,
            "order_qty": quantity,
        }
        return line_vals

    def shopify_set_tax_in_sale_order_line(self, instance, line, order_response, is_shipping, is_discount,
                                           previous_line, order_line_vals, is_duties):
        """ This method is used to set tax in the sale order line base on tax configuration in the
            Shopify setting in Odoo.
            :param line: Response of sale order line.
            :param order_response: Response of order.
            :param is_shipping: It used to identify that it a shipping line.
            :param is_discount: It used to identify that it a discount line.
            :param is_duties: It used to identify that it a duties line.
            :param previous_line: Record of the previously created sale order line.
            :param order_line_vals: Prepared sale order line vals as the previous method.
            @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 20 October 2020 .
            Task_id: 167537
        """
        if instance.apply_tax_in_order == "create_shopify_tax":
            taxes_included = order_response.get("taxes_included") or False
            tax_ids = []
            if line and line.get("tax_lines"):
                if line.get("taxable"):
                    # This is used for when the one product is taxable and another product is not
                    # taxable
                    tax_ids = self.shopify_get_tax_id_ept(instance,
                                                          line.get("tax_lines"),
                                                          taxes_included)
                if is_shipping:
                    # In the Shopify store there is configuration regarding tax is applicable on shipping or not,
                    # if applicable then this use.
                    tax_ids = self.shopify_get_tax_id_ept(instance,
                                                          line.get("tax_lines"),
                                                          taxes_included)
                if is_duties:
                    # In the Shopify store there is configuration regarding tax is applicable on line duties or not,
                    # if applicable then this use.
                    tax_ids = self.shopify_get_tax_id_ept(instance,
                                                          line.get("tax_lines"),
                                                          taxes_included)
            elif not line and previous_line:
                # Before modification, connector set order taxes on discount line but as per connector design,
                # we are creating discount line base on sale order line so it should apply sale order line taxes
                # in discount line not order taxes. It creates a problem while the customer is using multi taxes
                # in sale orders. so set the previous line taxes on the discount line.
                tax_ids = [(6, 0, previous_line.tax_id.ids)]
            order_line_vals["tax_id"] = tax_ids
            # When the one order with two products one product with tax and another product
            # without tax and apply the discount on order that time not apply tax on discount
            # which is
            if is_discount and not previous_line.tax_id:
                order_line_vals["tax_id"] = []
        return order_line_vals

    @api.model
    def shopify_get_tax_id_ept(self, instance, tax_lines, tax_included):
        """This method used to search tax in Odoo, If tax is not found in Odoo then it call child method to create a
            new tax in Odoo base on received tax response in order response.
            @return: tax_id
            @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 18/11/2019.
            Task Id : 157350
        """
        tax_id = []
        taxes = []
        company = instance.shopify_warehouse_id.company_id
        for tax in tax_lines:
            rate = float(tax.get("rate", 0.0))
            price = float(tax.get('price', 0.0))
            title = tax.get("title")
            rate = rate * 100
            if rate != 0.0 and price != 0.0:
                if tax_included:
                    name = "%s_(%s %s included)_%s" % (title, str(rate), "%", company.name)
                else:
                    name = "%s_(%s %s excluded)_%s" % (title, str(rate), "%", company.name)
                tax_id = self.env["account.tax"].search([("price_include", "=", tax_included),
                                                         ("type_tax_use", "=", "sale"), ("amount", "=", rate),
                                                         ("name", "=", name), ("company_id", "=", company.id)], limit=1)
                if not tax_id:
                    tax_id = self.sudo().shopify_create_account_tax(instance, rate, tax_included, company, name)
                if tax_id:
                    taxes.append(tax_id.id)
        if taxes:
            tax_id = [(6, 0, taxes)]
        return tax_id

    @api.model
    def shopify_create_account_tax(self, instance, value, price_included, company, name):
        """This method used to create tax in Odoo when importing orders from Shopify to Odoo.
            @param : self, value, price_included, company, name
            @return: account_tax_id
            @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 18/11/2019.
            Task Id : 157350
        """
        account_tax_obj = self.env["account.tax"]

        account_tax_id = account_tax_obj.create({"name": name, "amount": float(value),
                                                 "type_tax_use": "sale", "price_include": price_included,
                                                 "company_id": company.id})

        account_tax_id.mapped("invoice_repartition_line_ids").write(
            {"account_id": instance.invoice_tax_account_id.id if instance.invoice_tax_account_id else False})
        account_tax_id.mapped("refund_repartition_line_ids").write(
            {"account_id": instance.credit_tax_account_id.id if instance.credit_tax_account_id else False})

        return account_tax_id

    def prepare_vals_shopify_multi_payment(self, instance, order_data_queue_line, order_response, log_book_id,
                                           payment_gateway, workflow):
        """ This method is use to prepare a values for the multi payment.
            @author: Meera Sidapara @Emipro Technologies Pvt. Ltd on date 16/11/2021 .
            Task_id:179257 - Manage multiple payment.
        """
        payment_gateway_obj = self.env["shopify.payment.gateway.ept"]
        transactions = shopify.Transaction().find(order_id=order_response.get('id'))
        payment_list_vals = []
        for transaction in transactions:
            result = transaction.to_dict()
            if result.get('kind') in ['capture', 'sale'] and result.get('status') == 'success':
                payment_transaction_id = result.get('id')
                gateway = result.get('gateway')
                amount = result.get('amount')
                if order_response.get('gateway') == gateway:
                    payment_list = (0, 0, {'payment_gateway_id': payment_gateway.id, 'workflow_id': workflow.id,
                                           'amount': amount, 'payment_transaction_id': payment_transaction_id,
                                           'remaining_refund_amount': amount})
                    payment_list_vals.append(payment_list)
                    continue
                new_payment_gateway, new_workflow, payment_term = \
                    payment_gateway_obj.shopify_search_create_gateway_workflow(instance,
                                                                               order_data_queue_line,
                                                                               order_response,
                                                                               log_book_id,
                                                                               gateway)
                if not all([new_payment_gateway, new_workflow]):
                    return False
                payment_list = (0, 0, {'payment_gateway_id': new_payment_gateway.id, 'workflow_id': new_workflow.id,
                                       'amount': amount, 'payment_transaction_id': payment_transaction_id,
                                       'remaining_refund_amount': amount})
                payment_list_vals.append(payment_list)
        return payment_list_vals

    @api.model
    def closed_at(self, instance):
        """
        This method is used to close orders in the Shopify store after the update fulfillment
        from Odoo to the Shopify store.
        """
        sales_orders = self.search([('warehouse_id', '=', instance.shopify_warehouse_id.id),
                                    ('shopify_order_id', '!=', False),
                                    ('shopify_instance_id', '=', instance.id),
                                    ('state', '=', 'done'), ('closed_at_ept', '=', False)],
                                   order='date_order')

        instance.connect_in_shopify()

        for sale_order in sales_orders:
            order = shopify.Order.find(sale_order.shopify_order_id)
            order.close()
            sale_order.write({'closed_at_ept': datetime.now()})
        return True

    def get_shopify_carrier_code(self, picking):
        """
        Gives carrier name from picking, if available.
        @author: Maulik Barad on Date 16-Sep-2020.
        """
        carrier_name = ""
        if picking.carrier_id:
            carrier_name = picking.carrier_id.shopify_tracking_company or picking.carrier_id.shopify_source \
                           or picking.carrier_id.name or ''
        return carrier_name

    def prepare_tracking_numbers_and_lines_for_fulfilment(self, picking):
        """
        This method prepares tracking numbers' list and list of dictionaries of shopify line id and
        fulfilled qty for that.
        @author: Maulik Barad on Date 17-Sep-2020.
        Migration done by Haresh Mori on October 2021
        """
        shopify_line_ids = not self.is_service_tracking_updated and self.order_line.filtered(
            lambda l: l.shopify_line_id and l.product_id.type == "service" and not l.is_delivery and not
            l.is_gift_card_line).mapped("shopify_line_id") or []

        if picking.shopify_instance_id and not picking.shopify_instance_id.auto_fulfill_gift_card_order:
            shopify_line_ids = not self.is_service_tracking_updated and self.order_line.filtered(
                lambda l: l.shopify_line_id and l.product_id.type == "service" and
                          not l.is_delivery).mapped("shopify_line_id") or []
        moves = picking.move_lines
        product_moves = moves.filtered(lambda x: x.sale_line_id.product_id.id == x.product_id.id and x.state == "done")
        if picking.mapped("package_ids").filtered(lambda l: l.tracking_no):
            tracking_numbers, line_items = self.prepare_tracking_numbers_and_lines_for_multi_tracking_order(
                moves, product_moves)
        else:
            tracking_numbers, line_items = self.prepare_tracking_numbers_and_lines_for_simple_tracking_order(
                moves, product_moves, picking)
        for line in shopify_line_ids:
            quantity = sum(
                self.order_line.filtered(lambda l: l.shopify_line_id == line).mapped("product_uom_qty"))
            line_items.append({"id": line, "quantity": int(quantity)})
            self.write({"is_service_tracking_updated": True})

        return tracking_numbers, line_items

    def prepare_tracking_numbers_and_lines_for_simple_tracking_order(self, moves, product_moves, picking):
        """ This method is used to prepare tracking numbers and line items for the simple tracking order.
            :param moves: Move lines of picking.
            :param product_moves: Filtered moves.
            @return: tracking_numbers, line_items
            @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 20 October 2020 .
            Task_id: 167537
        """
        tracking_numbers = []
        line_items = []
        for move in product_moves.filtered(lambda line: line.product_id.detailed_type == 'product'):
            shopify_line_id = move.sale_line_id.shopify_line_id

            line_items.append({"id": shopify_line_id, "quantity": int(move.product_qty)})
            tracking_numbers.append(picking.carrier_tracking_ref or "")

        kit_sale_lines = moves.filtered(
            lambda x: x.sale_line_id.product_id.id != x.product_id.id and x.state == "done").sale_line_id
        for kit_sale_line in kit_sale_lines:
            shopify_line_id = kit_sale_line.shopify_line_id
            line_items.append({"id": shopify_line_id, "quantity": int(kit_sale_line.product_qty)})
            tracking_numbers.append(picking.carrier_tracking_ref or "")

        return tracking_numbers, line_items

    def prepare_tracking_numbers_and_lines_for_multi_tracking_order(self, moves, product_moves):
        """ This method is used to prepare tracking numbers and line items for the simple tracking order.
            :param moves: Move lines of picking.
            :param product_moves: Filtered moves.
            @return: tracking_numbers, line_items
            @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 20 October 2020 .
            Task_id: 167537
        """
        tracking_numbers = []
        line_items = []
        for move in product_moves:
            total_qty = 0
            shopify_line_id = move.sale_line_id.shopify_line_id

            for move_line in move.move_line_ids:
                tracking_no = move_line.result_package_id.tracking_no or ""
                total_qty += move_line.qty_done
                tracking_numbers.append(tracking_no)

            line_items.append({"id": shopify_line_id, "quantity": int(total_qty)})

        kit_move_lines = moves.filtered(
            lambda x: x.sale_line_id.product_id.id != x.product_id.id and x.state == "done")
        existing_sale_line_ids = []
        for move in kit_move_lines:
            if move.sale_line_id.id in existing_sale_line_ids:
                continue

            shopify_line_id = move.sale_line_id.shopify_line_id
            existing_sale_line_ids.append(move.sale_line_id.id)

            tracking_no = move.move_line_ids.result_package_id.mapped("tracking_no") or []
            tracking_no = tracking_no[0] if tracking_no else ""
            line_items.append({"id": shopify_line_id, "quantity": int(move.sale_line_id.product_uom_qty)})
            tracking_numbers.append(tracking_no)

        return tracking_numbers, line_items

    def update_order_status_in_shopify(self, instance, picking_ids=[]):
        """
        find the picking with below condition
            1. shopify_instance_id = instance.id
            2. updated_in_shopify = False
            3. state = Done
            4. location_dest_id.usage = customer
        get order line data from the picking and process on that. Process on only those products which type is
        not service get carrier_name from the picking get product qty from move lines. If one move having multiple
        move lines then total qty of all the move lines.
        shopify_line_id wise set the product qty_done set tracking details using shopify Fulfillment API update the
        order status
        @author: Maulik Barad on Date 16-Sep-2020.
        Task Id : 157905
        Migration done by Haresh Mori on October 2021
        """
        common_log_book_obj = self.env["common.log.book.ept"]
        common_log_line_obj = self.env["common.log.lines.ept"]

        model_id = common_log_line_obj.get_model_id(self._name)
        notify_customer = instance.notify_customer
        log_book = common_log_book_obj.create_common_log_book("export", 'shopify_instance_id', instance, model_id,
                                                              'shopify_ept')
        _logger.info(_("Update Order Status process start for '%s' Instance"), instance.name)

        instance.connect_in_shopify()
        if not picking_ids:
            picking_ids = self.shopify_search_picking_for_update_order_status(instance)
        for picking in picking_ids:
            carrier_name = self.get_shopify_carrier_code(picking)
            sale_order = picking.sale_id

            _logger.info("We are processing Sale order '%s' and Picking '%s'", sale_order.name, picking.name)
            is_continue_process, order_response = self.request_for_shopify_order(sale_order)
            if is_continue_process:
                continue
            order_lines = sale_order.order_line
            if order_lines and order_lines.filtered(
                    lambda s: s.product_id.detailed_type != 'service' and not s.shopify_line_id):
                message = (_(
                    "- Order status could not be updated for order %s.\n- Possible reason can be, Shopify order line "
                    "reference is missing, which is used to update Shopify order status at Shopify store. "
                    "\n- This might have happen because user may have done changes in order "
                    "manually, after the order was imported.", sale_order.name))
                _logger.info(message)
                self.create_shopify_log_line(message, False, log_book, sale_order.client_order_ref)
                continue

            tracking_numbers, line_items = sale_order.prepare_tracking_numbers_and_lines_for_fulfilment(picking)

            if not line_items:
                message = "No order lines found for the update order shipping status for order [%s]" \
                          % sale_order.name
                _logger.info(message)
                self.create_shopify_log_line(message, False, log_book, sale_order.client_order_ref)
                continue

            shopify_location_id = self.search_shopify_location_for_update_order_status(sale_order, instance, line_items,
                                                                                       log_book)

            if not shopify_location_id:
                continue

            fulfillment_vals = self.prepare_vals_for_fulfillment(sale_order, shopify_location_id, tracking_numbers,
                                                                 picking, carrier_name, line_items, notify_customer)

            is_create_mismatch, fulfillment_result, new_fulfillment = self.post_fulfilment_in_shopify(fulfillment_vals,
                                                                                                      sale_order,
                                                                                                      log_book)
            if is_create_mismatch:
                continue

            self.process_shopify_fulfilment_result(fulfillment_result, order_response, picking, sale_order, log_book,
                                                   new_fulfillment)

            sale_order.shopify_location_id = shopify_location_id

        if not log_book.log_lines:
            log_book.unlink()
            log_book = False

        if log_book and instance.is_shopify_create_schedule:
            message = []
            count = 0
            for log_line in log_book.log_lines:
                count += 1
                if count <= 5:
                    message.append('<' + 'li' + '>' + log_line.message + '<' + '/' + 'li' + '>')
            if count >= 5:
                message.append(
                    '<' + 'p' + '>' + 'Please refer the logbook' + '  ' + log_book.name + '  ' + 'check it in more detail' + '<' + '/' + 'p' + '>')
            note = "\n".join(message)
            self.create_schedule_activity_against_logbook(log_book, log_book.log_lines, note)

        self.closed_at(instance)
        return True

    def shopify_search_picking_for_update_order_status(self, instance):
        """ This method is used to search picking for the update order status.
            @return: picking_ids(Records of picking)
            @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 20 October 2020 .
            Task_id: 167537
            Migration done by Haresh Mori on October 2021
        """
        location_obj = self.env["stock.location"]
        stock_picking_obj = self.env["stock.picking"]
        customer_locations = location_obj.search([("usage", "=", "customer")])
        picking_ids = stock_picking_obj.search([("shopify_instance_id", "=", instance.id),
                                                ("updated_in_shopify", "=", False),
                                                ("state", "=", "done"),
                                                ("location_dest_id", "in", customer_locations.ids),
                                                ('is_cancelled_in_shopify', '=', False),
                                                ('is_manually_action_shopify_fulfillment', '=', False)],
                                               order="date")
        return picking_ids

    def request_for_shopify_order(self, sale_order):
        """ This method is used to request for sale order in the shopify store and if order response has
            fufillment_status is fulfilled then continue the update order status for that picking.
            @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 20 October 2020 .
            Task_id: 167537
            Migration done by Haresh Mori on October 2021
        """
        try:
            order = shopify.Order.find(sale_order.shopify_order_id)
            order_data = order.to_dict()
            if order_data.get('fulfillment_status') == 'fulfilled':
                _logger.info('Order %s is already fulfilled', sale_order.name)
                sale_order.picking_ids.filtered(lambda l: l.state == 'done').write({'updated_in_shopify': True})
                return True, order_data
            if order_data.get('cancelled_at') and order_data.get('cancel_reason'):
                sale_order.picking_ids.filtered(lambda l: l.state == 'done').write({'is_cancelled_in_shopify': True})
                return True, order_data
            return False, order_data
        except Exception as Error:
            _logger.info("Error in Request of shopify order for the fulfilment. Error: %s", Error)
            return True, {}

    def search_shopify_location_for_update_order_status(self, sale_order, instance, line_items, log_book):
        """ This method is used to search the shopify location for the update order status from Odoo to shopify store.
            @return: shopify_location_id
            @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 20 October 2020 .
            Task_id:167537
            Migration done by Haresh Mori on October 2021
        """
        shopify_location_obj = self.env["shopify.location.ept"]
        if instance.is_delivery_multi_warehouse:
            line_item_ids = [str(line.get('id')) for line in line_items]
            order_line = sale_order.order_line.filtered(
                lambda line: line.shopify_line_id in line_item_ids)
            shopify_location_id = shopify_location_obj.search(
                [('warehouse_for_order', '=', order_line.warehouse_id_ept.id), ("instance_id", "=", instance.id)])
            return shopify_location_id
        shopify_location_id = sale_order.shopify_location_id or False
        if not shopify_location_id:
            shopify_location_id = shopify_location_obj.search(
                [("warehouse_for_order", "=", sale_order.warehouse_id.id), ("instance_id", "=", instance.id),
                 ("is_primary_location", "=", True)])
            if not shopify_location_id:
                shopify_location_id = shopify_location_obj.search([("is_primary_location", "=", True),
                                                                   ("instance_id", "=", instance.id)])
            if not shopify_location_id:
                message = "Primary Location not found for instance %s while update order " \
                          "shipping status." % (
                              instance.name)
                _logger.info(message)
                self.create_shopify_log_line(message, False, log_book, sale_order.client_order_ref)
                return False

        return shopify_location_id

    def prepare_vals_for_fulfillment(self, sale_order, shopify_location_id, tracking_numbers, picking, carrier_name,
                                     line_items, notify_customer):
        """ This method is used to prepare a vals for the fulfillment.
            @return: fulfillment_vals
            @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 20 October 2020 .
            Task_id: 167537
            Migration done by Haresh Mori on October 2021
        """
        fulfillment_vals = {"order_id": sale_order.shopify_order_id,
                            "location_id": shopify_location_id.shopify_location_id,
                            "tracking_numbers": list(set(tracking_numbers)),
                            "tracking_urls": [picking.carrier_tracking_url or ''],
                            "tracking_company": carrier_name, "line_items": line_items,
                            "notify_customer": notify_customer}
        return fulfillment_vals

    def post_fulfilment_in_shopify(self, fulfillment_vals, sale_order, log_book):
        """ This method is used to post the fulfillment from Odoo to Shopify store.
            @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 10 November 2020 .
            Task_id: 167930 - Update order status changes as per v13
            Migration done by Haresh Mori on October 2021
        """
        new_fulfillment = False
        fulfillment_result = False
        try:
            new_fulfillment = shopify.Fulfillment(fulfillment_vals)
            fulfillment_result = new_fulfillment.save()
            if not fulfillment_result:
                return False, fulfillment_result, new_fulfillment
        except ClientError as error:
            if hasattr(error, "response") and error.response.code == 429 and error.response.msg == "Too Many Requests":
                time.sleep(int(float(error.response.headers.get('Retry-After', 5))))
                fulfillment_result = new_fulfillment.save()
        except Exception as error:
            message = "%s" % str(error)
            _logger.info(message)
            self.create_shopify_log_line(message, False, log_book, sale_order.client_order_ref)
            return True, fulfillment_result, new_fulfillment

        return False, fulfillment_result, new_fulfillment

    def process_shopify_fulfilment_result(self, fulfillment_result, order_response, picking, sale_order, log_book,
                                          new_fulfillment):
        """ This method is used to process fulfillment result.
            @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 10 November 2020 .
            Task_id:167930 - Update order status changes as per v13
            Migration done by Haresh Mori on October 2021
        """
        if not fulfillment_result:
            if order_response.get('fulfillment_status') == 'partial':
                if not new_fulfillment.errors:
                    picking.write({'updated_in_shopify': True})
            else:
                picking.write({'is_manually_action_shopify_fulfillment': True})
            sale_order.write({'is_service_tracking_updated': False})
            message = "Order(%s) status not updated due to some issue in fulfillment request/response:" % (
                sale_order.name)
            _logger.info(message)
            self.create_shopify_log_line(message, False, log_book, sale_order.client_order_ref)
            return False

        fulfillment_id = ''
        if new_fulfillment:
            shopify_fullment_result = xml_to_dict(new_fulfillment.to_xml())
            if shopify_fullment_result:
                fulfillment_id = shopify_fullment_result.get('fulfillment').get('id') or ''

        picking.write({'updated_in_shopify': True, 'shopify_fulfillment_id': fulfillment_id})

        return True

    @api.model
    def process_shopify_order_via_webhook(self, order_data, instance, update_order=False):
        """
        Creates order data queue and process it.
        This method is for order imported via create and update webhook.
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 10-Jan-2020..
        @param order_data: Dictionary of order's data.
        @param instance: Instance of Shopify.
        @param update_order: If update order webhook id called.
        """
        order_queue_obj = self.env["shopify.order.data.queue.ept"]
        order_queue_line_obj = self.env["shopify.order.data.queue.line.ept"]
        queue_type = 'unshipped'
        if order_data.get('fulfillment_status') == 'fulfilled':
            queue_type = 'shipped'
        queue = order_queue_line_obj.create_order_data_queue_line([order_data],
                                                                  instance,
                                                                  queue_type,
                                                                  created_by='webhook')
        if not update_order:
            order_queue_obj.browse(queue).order_data_queue_line_ids.process_import_order_queue_data()
        self._cr.commit()
        return True

    @api.model
    def update_shopify_order(self, queue_lines, log_book, created_by):
        """
        This method will update order as per its status got from Shopify.
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 13-Jan-2020..
        @param queue_lines: Order Data Queue Line.
        @param log_book: Common Log Book.
        @param created_by: Queue line Created by.
        @return: Updated Sale order.
        """
        common_log_line_obj = self.env["common.log.lines.ept"]
        orders = self
        for queue_line in queue_lines:
            message = ""
            shopify_instance = queue_line.shopify_instance_id
            order_data = json.loads(queue_line.order_data)
            shopify_status = order_data.get("financial_status")
            order = self.search_existing_shopify_order(order_data, shopify_instance, order_data.get("order_number"))

            if not order:
                self.import_shopify_orders(queue_line, log_book)
                return True

            # Below condition use for, In shopify store there is full refund.
            if order_data.get('cancel_reason'):
                cancelled = order.cancel_shopify_order()
                if not cancelled:
                    message = "System can not cancel the order {0} as one of the Delivery Order " \
                              "related to it is in the 'Done' status.".format(order.name)
            if shopify_status == "refunded" or "partially_refunded" and order_data.get("refunds"):
                message = self.create_shipped_order_refund(shopify_status, order_data, order, created_by)
            #     if not message:
            #         total_refund = 0.0
            #         for refund in order_data.get('refunds'):
            #             for transaction in refund.get('transactions'):
            #                 if transaction.get('kind') == 'refund' and transaction.get('status') == 'success':
            #                     total_refund += float(transaction.get('amount'))
            #         refunded = order.create_shopify_refund(order_data.get("refunds"), total_refund, created_by)
            #         if refunded[0] == 0:
            #             message = "- Refund can only be generated if it's related order " \
            #                       "invoice is found.\n- For order [%s], system could not find the " \
            #                       "related order invoice. " % (order_data.get('name'))
            #         elif refunded[0] == 2:
            #             message = "- Refund can only be generated if it's related order " \
            #                       "invoice is in 'Post' status.\n- For order [%s], system found " \
            #                       "related invoice but it is not in 'Post' status." % (
            #                           order_data.get('name'))
            #         elif refunded[0] == 3:
            #             message = "- Partial refund is received from Shopify for order [%s].\n " \
            #                       "- System do not process partial refunds.\n" \
            #                       "- Either create partial refund manually in Odoo or do full " \
            #                       "refund in Shopify." % (order_data.get('name'))
            # elif shopify_status == "partially_refunded" and order_data.get("refunds"):
            #     message = order.create_shopify_partially_refund(order_data.get("refunds"), order_data.get('name'),
            #                                                     created_by)
            # Below condition use for, In shopify store there is fulfilled order.
            elif order_data.get('fulfillment_status') == 'fulfilled':
                fulfilled = order.fulfilled_shopify_order()
                if isinstance(fulfilled, bool) and not fulfilled:
                    message = "There is not enough stock to complete Delivery for order [" \
                              "%s]" % order_data.get('name')
                elif not fulfilled:
                    message = "There is not enough stock to complete Delivery for order [" \
                              "%s]" % order_data.get('name')
            # self.prepare_vals_shopify_multi_payment_refund(order_data.get("refunds"), order)
            if message:
                model_id = common_log_line_obj.get_model_id(self._name)
                common_log_line_obj.shopify_create_order_log_line(message, model_id,
                                                                  queue_line, log_book)
                queue_line.write({'state': 'failed', 'processed_at': datetime.now()})
            else:
                queue_line.state = "done"
        return orders

    def cancel_shopify_order(self):
        """
        Cancelled the sale order when it is cancelled in Shopify Store with full refund.
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 13-Jan-2020..
        """
        if "done" in self.picking_ids.mapped("state"):
            for picking_id in self.picking_ids:
                picking_id.write({'updated_in_shopify': True})
                picking_id.message_post(
                    body=_("Order %s has been canceled in the Shopify store.", self.shopify_order_number))
            return False
        self.action_cancel()
        self.canceled_in_shopify = True
        return True

    # def create_shopify_refund(self, refunds_data, total_refund, created_by=""):
    #     """
    #     Creates refund of shopify order, when order is refunded in Shopify.
    #     It will need invoice created and posted for creating credit note in Odoo, otherwise it will
    #     create log and generate activity as per configuration.
    #     @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 13-Jan-2020..
    #     @param refunds_data: Data of refunds.
    #     @param total_refund: Total refund amount.
    #     @param created_by: created by refund.
    #     @return:[0] : When no invoice is created.
    #             [1] : When invoice is not posted.
    #             [2] : When partial refund was made in Shopify.
    #             [True]:When credit notes are created or partial refund is done.
    #     """
    #     if not self.invoice_ids:
    #         return [0]
    #     invoices = self.invoice_ids.filtered(lambda x: x.move_type == "out_invoice")
    #     refunds = self.invoice_ids.filtered(lambda x: x.move_type == "out_refund")
    #     refund_date = self.convert_order_date(refunds_data[0])
    #     if refunds:
    #         return [True]
    #
    #     for invoice in invoices:
    #         if not invoice.state == "posted":
    #             return [2]
    #     if self.amount_total == total_refund:
    #         move_reversal = self.env["account.move.reversal"].with_context(
    #             {"active_model": "account.move", "active_ids": invoices[0].ids}).create(
    #             {"refund_method": "refund", "date": refund_date,
    #              "reason": "Refunded from shopify" if len(refunds_data) > 1 else refunds_data[0].get("note"),
    #              "journal_id": invoices[0].journal_id.id})
    #         move_reversal.reverse_moves()
    #         move_reversal.new_move_ids.message_post(body=_("Credit note generated by %s as Order refunded in "
    #                                                        "Shopify.", created_by))
    #         move_reversal.new_move_ids.write(
    #             {"is_refund_in_shopify": True, "shopify_refund_id": refunds_data[0].get('id')})
    #         return [True]
    #     return [3]

    def fulfilled_shopify_order(self):
        """
        If order is not confirmed yet, confirms it first.
        Make the picking done, when order will be fulfilled in Shopify.
        This method is used for Update order webhook.
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 13-Jan-2020..
        """
        if self.state not in ["sale", "done", "cancel"]:
            self.action_confirm()
        return self.fulfilled_picking_for_shopify(self.picking_ids.filtered(lambda x:
                                                                            x.location_dest_id.usage
                                                                            == "customer"))

    def fulfilled_picking_for_shopify(self, pickings):
        """
        It will make the pickings done.
        This method is used for Update order webhook.
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 13-Jan-2020..
        """
        skip_sms = {"skip_sms": True}
        for picking in pickings.filtered(lambda x: x.state not in ['cancel', 'done']):
            if picking.state != "assigned":
                if picking.move_lines.move_orig_ids:
                    completed = self.fulfilled_picking_for_shopify(picking.move_lines.move_orig_ids.picking_id)
                    if not completed:
                        return False
                picking.action_assign()
                # # Add by Vrajesh Dt.01/04/2020 automatically validate delivery when import POS
                # order in shopify
                if picking.sale_id and (
                        picking.sale_id.is_pos_order or picking.sale_id.shopify_order_status == "fulfilled"):
                    for move_id in picking.move_ids_without_package:
                        vals = self.prepare_vals_for_move_line(move_id, picking)
                        picking.move_line_ids.create(vals)
                    picking.action_done()
                    return True
                if picking.state != "assigned":
                    return False
            result = picking.with_context(**skip_sms).button_validate()
            if isinstance(result, dict):
                dict(result.get("context")).update(skip_sms)
                context = result.get("context")  # Merging dictionaries.
                model = result.get("res_model", "")
                # model can be stock.immediate.transfer or stock backorder.confirmation
                if model:
                    record = self.env[model].with_context(context).create({})
                    record.process()
            if picking.state == "done":
                picking.message_post(body=_("Picking is done by Webhook as Order is fulfilled in Shopify."))
                pickings.updated_in_shopify = True
                return result
        return True

    def prepare_vals_for_move_line(self, move_id, picking):
        """ This method used to prepare a vals for move line.
            @return: vals
            @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 20 October 2020 .
            Task_id: 167537
        """
        vals = {
            'product_id': move_id.product_id.id,
            'product_uom_id': move_id.product_id.uom_id.id,
            'qty_done': move_id.product_uom_qty,
            'location_id': move_id.location_id.id,
            'picking_id': picking.id,
            'location_dest_id': move_id.location_dest_id.id,
        }
        return vals

    def create_shopify_partially_refund(self, refunds_data, order_name, created_by="", shopify_financial_status=""):
        """This method is used to check the required validation before create
            a partial refund and call child methods for a partial refund.
            @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 17/05/2021.
            Task Id : 173066 - Manage Partial refund in the Shopify
        """
        account_move_obj = self.env['account.move']
        message = False
        if shopify_financial_status == "refunded":
            shopify_financial_status = "Refunded"
        else:
            shopify_financial_status = "Partially Refunded"
        if not self.invoice_ids:
            message = "- Partially refund can only be generated if it's related order " \
                      "invoice is found.\n- For order [%s], system could not find the " \
                      "related order invoice. " % order_name
            return message
        refund_invoices = self.invoice_ids.filtered(lambda x: x.move_type == "out_refund" and x.state == "posted")
        if refund_invoices:
            total_refund_amount = 0.0
            for refund_invoice in refund_invoices:
                total_refund_amount += refund_invoice.amount_total
            if total_refund_amount == self.amount_total:
                return
        invoices = self.invoice_ids.filtered(lambda x: x.move_type == "out_invoice")
        for invoice in invoices:
            if not invoice.state == "posted":
                message = "- Partially refund can only be generated if it's related order " \
                          "invoice is in 'Post' status.\n- For order [%s], system found " \
                          "related invoice but it is not in 'Post' status." % order_name
                return message
        for refund_data_line in refunds_data:
            existing_refund = account_move_obj.search([("shopify_refund_id", "=", refund_data_line.get('id')),
                                                       ("shopify_instance_id", "=", self.shopify_instance_id.id)])
            if existing_refund:
                continue
            new_move = self.with_context(check_move_validity=False).create_move_and_delete_not_necessary_line(
                refund_data_line, invoices, created_by, shopify_financial_status)
            if refund_data_line.get('order_adjustments'):
                self.create_refund_adjustment_line(refund_data_line.get('order_adjustments'), new_move)
            new_move.with_context(check_move_validity=False)._recompute_dynamic_lines()
            if new_move.state == 'draft':
                new_move.action_post()
        return message

    def create_move_and_delete_not_necessary_line(self, refunds_data, invoices, created_by, shopify_financial_status):
        """This method is used to create a reverse move of invoice and delete the invoice lines from the newly
            created move which product not refunded in Shopify.
            @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 19/05/2021.
            Task Id : 173066 - Manage Partial refund in the Shopify
        """
        delete_move_lines = self.env['account.move.line']
        shopify_line_ids = []
        shopify_line_ids_with_qty = {}
        for refund_line in refunds_data.get('refund_line_items'):
            shopify_line_ids.append(refund_line.get('line_item_id'))
            shopify_line_ids_with_qty.update({refund_line.get('line_item_id'): refund_line.get('quantity')})

        refund_date = self.convert_order_date(refunds_data)
        move_reversal = self.env["account.move.reversal"].with_context(
            {"active_model": "account.move", "active_ids": invoices[0].ids}, check_move_validity=False).create(
            {"refund_method": "refund",
             "reason": "Partially Refunded from shopify" if len(refunds_data) > 1 else refunds_data.get("note"),
             "journal_id": invoices[0].journal_id.id, "date": refund_date})

        move_reversal.reverse_moves()
        new_move = move_reversal.new_move_ids
        new_move.write({'is_refund_in_shopify': True, 'shopify_refund_id': refunds_data.get('id')})
        total_qty = 0.0
        for new_move_line in new_move.invoice_line_ids:
            shopify_line_id = new_move_line.sale_line_ids.shopify_line_id
            if new_move_line.product_id.id == self.shopify_instance_id.discount_product_id.id:
                new_move_line.price_unit = new_move_line.price_unit / total_qty
            elif shopify_line_id and int(shopify_line_id) not in shopify_line_ids:
                delete_move_lines += new_move_line
                # delete_move_lines.recompute_tax_line = True
            else:
                total_qty += new_move_line.sale_line_ids.product_uom_qty
                new_move_line.quantity = shopify_line_ids_with_qty.get(int(shopify_line_id))
                new_move_line.recompute_tax_line = True
                # self.set_price_based_on_refund(new_move_line)

        new_move.message_post(body=_("Credit note generated by %s as Order %s "
                                     "in Shopify. This credit note has been created from "
                                     "<a href=# data-oe-model=sale.order data-oe-id=%d>%s</a>") % (
                                       created_by, shopify_financial_status, self.id, self.name))
        self.message_post(body=_(
            "Credit note created <a href=# data-oe-model=account.move data-oe-id=%d>%s</a> via %s") % (
                                   new_move.id, new_move.name, created_by))

        if delete_move_lines:
            delete_move_lines.with_context(check_move_validity=False).write({'quantity': 0})
            delete_move_lines.with_context(check_move_validity=False)._onchange_price_subtotal()
            # delete_move_lines.with_context(check_move_validity=False).unlink()
            new_move.with_context(check_move_validity=False)._recompute_tax_lines()
        return new_move

    def set_price_based_on_refund(self, move_line):
        """
        Calculate tax price based on quantity and set in move line amount.
        @author: Meera Sidapara @Emipro Technologies Pvt. Ltd on date 01/07/2022.
        Task Id : 194381 - Shopify refund issue fix
        """
        total_adjust_amount = 0.0
        for line in move_line.sale_line_ids:
            if move_line.quantity != line.product_uom_qty:
                tax_dict = json.loads(line.order_id.tax_totals_json)
                sub_total_tax_dict = tax_dict.get('groups_by_subtotal').get('Untaxed Amount')
                total_tax_amount = 0.0
                if sub_total_tax_dict:
                    for tax in sub_total_tax_dict:
                        total_tax_amount += tax.get('tax_group_amount')
                    total_adjust_amount = total_tax_amount / line.product_uom_qty
        move_line.price_unit += total_adjust_amount
        return True

    def create_refund_adjustment_line(self, order_adjustments, move_ids):
        """This method is used to create an invoice line in a new move to manage the adjustment refund.
            @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 19/05/2021.
            Task Id : 173066 - Manage Partial refund in the Shopify
        """
        account_move_line_obj = self.env['account.move.line']
        adjustment_product = self.env.ref('shopify_ept.shopify_refund_adjustment_product', False)
        adjustments_amount = 0.0
        for order_adjustment in order_adjustments:
            adjustments_amount += float(order_adjustment.get('amount', 0.0))
        if abs(adjustments_amount) > 0:
            move_vals = {'product_id': adjustment_product.id, 'quantity': 1, 'price_unit': -adjustments_amount,
                         'move_id': move_ids.id, 'partner_id': move_ids.partner_id.id,
                         'name': adjustment_product.display_name}
            new_move_vals = account_move_line_obj.new(move_vals)
            new_move_vals._onchange_product_id()
            new_vals = account_move_line_obj._convert_to_write(
                {name: new_move_vals[name] for name in new_move_vals._cache})
            new_vals.update({'quantity': 1, 'price_unit': -adjustments_amount, 'tax_ids': []})
            account_move_line_obj.with_context(check_move_validity=False).create(new_vals)

    def _prepare_invoice(self):
        """This method used set a shopify instance in customer invoice.
            @param : self
            @return: inv_val
            @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 20/11/2019.
            Task Id : 157911
        """
        inv_val = super(SaleOrder, self)._prepare_invoice()
        if self.shopify_instance_id:
            inv_val.update({'shopify_instance_id': self.shopify_instance_id.id, 'is_shopify_multi_payment':
                self.is_shopify_multi_payment})
        return inv_val

    def action_open_cancel_wizard(self):
        """This method used to open a wizard to cancel order in Shopify.
            @param : self
            @return: action
            @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 20/11/2019.
            Task Id : 157911
        """
        view = self.env.ref('shopify_ept.view_shopify_cancel_order_wizard')
        context = dict(self._context)
        context.update({'active_model': 'sale.order', 'active_id': self.id, 'active_ids': self.ids})
        return {
            'name': _('Cancel Order In Shopify'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'shopify.cancel.refund.order.wizard',
            'views': [(view.id, 'form')],
            'view_id': view.id,
            'target': 'new',
            'context': context
        }

    def process_order_fullfield_qty(self, order_response):
        """ This method is used to search order line which product qty need to create stock move.
            :param order_response: Response of shopify order.
            @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 31 December 2020 .
            Task_id: 169381 - Gift card order import changes
        """
        module_obj = self.env['ir.module.module']
        mrp_module = module_obj.sudo().search([('name', '=', 'mrp'), ('state', '=', 'installed')])
        lines = order_response.get("line_items")
        bom_lines = []
        for line in lines:
            shopify_line_id = line.get('id')
            sale_order_line = self.order_line.filtered(lambda order_line: int(order_line.shopify_line_id)
                                                                          == shopify_line_id and
                                                                          order_line.product_id.detailed_type != 'service')
            if not sale_order_line:
                continue
            fulfilled_qty = float(line.get('quantity')) - float(line.get('fulfillable_quantity'))
            if mrp_module:
                bom_lines = self.check_for_bom_product(sale_order_line.product_id)
            for bom_line in bom_lines:
                self.create_stock_move_of_fullfield_qty(sale_order_line, fulfilled_qty, bom_line)
            if fulfilled_qty > 0 and not mrp_module:
                self.create_stock_move_of_fullfield_qty(sale_order_line, fulfilled_qty)
        return True

    def create_stock_move_of_fullfield_qty(self, order_line, fulfilled_qty, bom_line=False):
        """ This method is used to create stock move which product qty is fullfield.
            :param order_line: Record of sale order line
            :param fulfilled_qty: Qty of product which needs to create a stock move.
            :param bom_line: Record of bom line
            @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 31 December 2020 .
            Task_id: 169381 - Gift card order import changes
        """
        stock_location_obj = self.env["stock.location"]
        customer_location = stock_location_obj.search([("usage", "=", "customer")], limit=1)
        if bom_line:
            product = bom_line[0].product_id
            product_qty = bom_line[1].get('qty', 0) * fulfilled_qty
            product_uom = bom_line[0].product_uom_id
        else:
            product = order_line.product_id
            product_qty = fulfilled_qty
            product_uom = order_line.product_uom
        if product and product_qty and product_uom:
            move_vals = self.prepare_val_for_stock_move(product, product_qty, product_uom, customer_location,
                                                        order_line)
            if bom_line:
                move_vals.update({'bom_line_id': bom_line[0].id})
            stock_move = self.env['stock.move'].create(move_vals)
            stock_move._action_assign()
            stock_move._set_quantity_done(fulfilled_qty)
            stock_move._action_done()
        return True

    def prepare_val_for_stock_move(self, product, fulfilled_qty, product_uom, customer_location, order_line):
        """ Prepare vals for the stock move.
            @return vals
            @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 31 December 2020 .
            Task_id: 169381 - Gift card order import changes
        """
        vals = {
            'name': _('Auto processed move : %s') % product.display_name,
            'company_id': self.company_id.id,
            'product_id': product.id if product else False,
            'product_uom_qty': fulfilled_qty,
            'product_uom': product_uom.id if product_uom else False,
            'location_id': self.warehouse_id.lot_stock_id.id,
            'location_dest_id': customer_location.id,
            'state': 'confirmed',
            'sale_line_id': order_line.id
        }
        return vals

    def _get_invoiceable_lines(self, final=False):
        """Inherited base method to manage tax rounding in the invoice.
            @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 14 May 2021.
            173531 - shopify tax rounding issue
        """
        if self.shopify_instance_id:
            self.env.context = dict(self._context)
            self.env.context.update({'round': False})
        invoiceable_lines = super(SaleOrder, self)._get_invoiceable_lines(final)
        return invoiceable_lines

    def paid_invoice_ept(self, invoices):
        """
        Override the common connector library method here to create separate payment records.
        Override by Meera Sidapara on date 16/11/2021.
        """
        self.ensure_one()
        account_payment_obj = self.env['account.payment']
        if self.is_shopify_multi_payment:
            for invoice in invoices:
                if invoice.amount_residual:
                    for payment in self.shopify_payment_ids:
                        vals = invoice.prepare_payment_dict(payment.workflow_id)
                        vals.update({'amount': payment.amount})
                        payment_id = account_payment_obj.create(vals)
                        payment_id.action_post()
                        self.reconcile_payment_ept(payment_id, invoice)
            return True
        super(SaleOrder, self).paid_invoice_ept(invoices)

    def create_schedule_activity_against_logbook(self, log_book_id, mismatch_record, note):
        """
        Author : Meera Sidapara 27/10/2021 this method use for create schedule activity based on
        log book.
        :model: model use for the model
        :return: True
        Task Id: 179264
        """
        mail_activity_obj = self.env['mail.activity']
        ir_model_obj = self.env['ir.model']
        model_id = ir_model_obj.search([('model', '=', 'common.log.book.ept')])
        activity_type_id = log_book_id and log_book_id.shopify_instance_id.shopify_activity_type_id.id
        date_deadline = datetime.strftime(
            datetime.now() + timedelta(days=int(log_book_id.shopify_instance_id.shopify_date_deadline)), "%Y-%m-%d")
        if len(mismatch_record) > 0:
            for user_id in log_book_id.shopify_instance_id.shopify_user_ids:
                mail_activity = mail_activity_obj.search([('res_model_id', '=', model_id.id),
                                                          ('user_id', '=', user_id.id),
                                                          ('res_name', '=', log_book_id.name),
                                                          ('activity_type_id', '=', activity_type_id)])
                note_2 = "<p>" + note + '</p>'
                if not mail_activity or mail_activity.note != note_2:
                    vals = {'activity_type_id': activity_type_id, 'note': note, 'summary': log_book_id.name,
                            'res_id': log_book_id.id, 'user_id': user_id.id or self._uid,
                            'res_model_id': model_id.id, 'date_deadline': date_deadline}
                    try:
                        mail_activity_obj.create(vals)
                    except Exception as error:
                        _logger.info("Unable to create schedule activity, Please give proper "
                                     "access right of this user :%s  ", user_id.name)
                        _logger.info(error)
        return True

    def action_order_ref_redirect(self):
        """
        This method is used to redirect Woocommerce order in WooCommerce Store.
        @author: Meera Sidapara on Date 31-May-2022.
        @Task: 190111 - Shopify APP features
        """
        self.ensure_one()
        url = '%s/admin/orders/%s' % (self.shopify_instance_id.shopify_host, self.shopify_order_id)
        return {
            'type': 'ir.actions.act_url',
            'url': url,
            'target': 'new',
        }


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    shopify_line_id = fields.Char("Shopify Line", copy=False)
    is_gift_card_line = fields.Boolean(copy=False, default=False)

    def unlink(self):
        """
        This method is used to prevent the delete sale order line if the order has a Shopify order.
        @author: Haresh Mori on date:17/06/2020
        """
        for record in self:
            if record.order_id.shopify_order_id:
                msg = _(
                    "You can not delete this line because this line is Shopify order line and we need "
                    "Shopify line id while we are doing update order status")
                raise UserError(msg)
        return super(SaleOrderLine, self).unlink()


class ImportShopifyOrderStatus(models.Model):
    _name = "import.shopify.order.status"
    _description = 'Order Status'

    name = fields.Char()
    status = fields.Char()
