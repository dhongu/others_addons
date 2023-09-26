# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.
import logging
from odoo import models, api, fields, _
from odoo.tools.misc import format_date

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _compute_stock_move(self):
        """
        Find all stock moves associated with the order.
        @author: Keyur Kanani
        Migration done by Haresh Mori on September 2021
        """
        self.moves_count = self.env["stock.move"].search_count([("picking_id", "=", False),
                                                                ("sale_line_id", "in", self.order_line.ids)])

    auto_workflow_process_id = fields.Many2one("sale.workflow.process.ept", string="Workflow Process", copy=False)
    moves_count = fields.Integer(compute="_compute_stock_move", string="Stock Move", store=False,
                                 help="Stock Move Count for Orders without Picking.")

    def create_sales_order_vals_ept(self, vals):
        """
        @param vals: Vals of sale order.
        @return: Vals of sales order after call onchange method.
        Migration done by Haresh Mori on September 2021
        """
        sale_order = self.env['sale.order']
        order_vals = {
            'company_id': vals.get('company_id', False),
            'partner_id': vals.get('partner_id', False),
            'partner_invoice_id': vals.get('partner_invoice_id', False),
            'partner_shipping_id': vals.get('partner_shipping_id', False),
            'warehouse_id': vals.get('warehouse_id', False),
        }

        new_record = sale_order.new(order_vals)
        # Return Pricelist- Payment terms- Invoice address- Delivery address
        new_record.onchange_partner_id()
        order_vals = sale_order._convert_to_write({name: new_record[name] for name in new_record._cache})

        # Return Fiscal Position
        order_vals.update({'partner_shipping_id': vals.get('partner_shipping_id', False)})
        new_record = sale_order.new(order_vals)
        new_record.onchange_partner_shipping_id()
        order_vals = sale_order._convert_to_write({name: new_record[name] for name in new_record._cache})

        fpos = order_vals.get('fiscal_position_id') or vals.get('fiscal_position_id', False)
        new_vals = self.prepare_order_vals_after_onchange_ept(vals, fpos)
        order_vals.update(new_vals)
        return order_vals

    def prepare_order_vals_after_onchange_ept(self, vals, fpos):
        """ This method is used to prepare order vals after onchange methods call..
            @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 21 September 2021 .
        """
        order_vals = {
            'company_id': vals.get('company_id', False),
            'picking_policy': vals.get('picking_policy'),
            'partner_invoice_id': vals.get('partner_invoice_id', False),
            'partner_id': vals.get('partner_id', False),
            'partner_shipping_id': vals.get('partner_shipping_id', False),
            'date_order': vals.get('date_order', False),
            'state': 'draft',
            'pricelist_id': vals.get('pricelist_id', False),
            'fiscal_position_id': fpos,
            'payment_term_id': vals.get('payment_term_id', False),
            'team_id': vals.get('team_id', False),
            'client_order_ref': vals.get('client_order_ref', ''),
            'carrier_id': vals.get('carrier_id', False)
        }
        return order_vals

    @api.onchange('partner_shipping_id', 'partner_id')
    def onchange_partner_shipping_id(self):
        """
        Inherited method for setting fiscal position by warehouse.
        """
        res = super(SaleOrder, self).onchange_partner_shipping_id()
        fiscal_position = self.get_fiscal_position_by_warehouse()
        self.fiscal_position_id = fiscal_position
        return res

    @api.onchange('warehouse_id')
    def onchange_warehouse_id(self):
        """
        This method for sets fiscal position, when warehouse is changed.
        """
        fiscal_position = self.get_fiscal_position_by_warehouse()
        self.fiscal_position_id = fiscal_position

    def get_fiscal_position_by_warehouse(self):
        """
        This method will give fiscal position from warehouse.
        """
        fiscal_position = self.fiscal_position_id
        warehouse = self.warehouse_id

        if warehouse and self.partner_id and self.partner_id.allow_search_fiscal_based_on_origin_warehouse:
            origin_country_id = warehouse.partner_id and warehouse.partner_id.country_id and \
                                warehouse.partner_id.country_id.id or False
            origin_country_id = origin_country_id or (warehouse.company_id.partner_id.country_id
                                                      and warehouse.company_id.partner_id.country_id.id or False)
            is_amz_customer = getattr(self.partner_id, 'is_amz_customer', False)
            is_bol_customer = getattr(self.partner_id, 'is_bol_customer', False)
            fiscal_position = self.env['account.fiscal.position'].with_context(
                origin_country_ept=origin_country_id, is_amazon_fpos=is_amz_customer,is_bol_fpos=is_bol_customer).with_company(
                warehouse.company_id.id).get_fiscal_position(self.partner_id.id, self.partner_shipping_id.id)

        return fiscal_position

    def action_view_stock_move_ept(self):
        """
        List all stock moves which is associated with the Order.
        @author: Keyur Kanani
        Migration done by Haresh Mori on September 2021
        """
        stock_move_obj = self.env['stock.move']
        move_ids = stock_move_obj.search([('picking_id', '=', False), ('sale_line_id', 'in', self.order_line.ids)]).ids
        action = {
            'domain': "[('id', 'in', " + str(move_ids) + " )]",
            'name': 'Order Stock Move',
            'view_mode': 'tree,form',
            'res_model': 'stock.move',
            'type': 'ir.actions.act_window',
        }
        return action

    def _prepare_invoice(self):
        """
        This method would let the invoice date will be the same as the order date and also set the sale journal.
        Migration done by Haresh Mori on September 2021
        """
        invoice_vals = super(SaleOrder, self)._prepare_invoice()
        if self.auto_workflow_process_id:
            if self.auto_workflow_process_id.sale_journal_id:
                invoice_vals.update({'journal_id': self.auto_workflow_process_id.sale_journal_id.id})
            if self.auto_workflow_process_id.invoice_date_is_order_date:
                invoice_vals.update({"date": self.date_order.date(), "invoice_date": fields.Date.context_today(self)})
        return invoice_vals

    def validate_order_ept(self):
        """
        This function validate sales order and write date_order same as previous date because Odoo changes date_order
        to current date in action confirm process.
        @author: Dipesh Tanna
        Added invalidate_cache line to resolve the issue of PO line description while product route has dropship and
        multi language active in Odoo.T-07778 Added line by Haresh Mori @Emipro Technologies Pvt. Ltd on date 19 July
        2021
        Migration done by Haresh Mori on September 2021
        """
        self.ensure_one()
        date_order = self.date_order
        self.env['product.product'].invalidate_cache(fnames=['display_name'])
        self.action_confirm()
        self.write({'date_order': date_order})
        return True

    def process_orders_and_invoices_ept(self):
        """
        This method will confirm sale orders, create and paid related invoices.
        Migration done by Haresh Mori on September 2021
        """
        for order in self:
            work_flow_process_record = order.auto_workflow_process_id

            if order.invoice_status and order.invoice_status == 'invoiced':
                continue
            if work_flow_process_record.validate_order:
                order.validate_order_ept()

            order_lines = order.mapped('order_line').filtered(lambda l: l.product_id.invoice_policy == 'order')
            if not order_lines.filtered(lambda l: l.product_id.type == 'product') and len(
                order.order_line) != len(order_lines.filtered(lambda l: l.product_id.type in ['service', 'consu'])):
                continue

            order.validate_and_paid_invoices_ept(work_flow_process_record)
        return True

    def validate_and_paid_invoices_ept(self, work_flow_process_record):
        """
        This method will create invoices, validate it and register payment it, according to the configuration in
        workflow sets in quotation.
        :param work_flow_process_record:
        :return: It will return boolean.
        Migration done by Haresh Mori on September 2021
        """
        self.ensure_one()
        if work_flow_process_record.create_invoice:
            if work_flow_process_record.invoice_date_is_order_date:
                fiscalyear_lock_date = self.company_id._get_user_fiscal_lock_date()
                if self.date_order.date() <= fiscalyear_lock_date:
                    log_book_id = self._context.get('log_book_id')
                    if log_book_id:
                        message = "You cannot create invoice for order (%s) " \
                                  "prior to and inclusive of the lock date %s. " \
                                  "So, order is created but invoice is not created." % (self.name, format_date(
                            self.env, fiscalyear_lock_date))
                        self.env['common.log.lines.ept'].create({
                            'message': message,
                            'order_ref': self.name,
                            'log_book_id': log_book_id
                        })
                        _logger.info(message)
                    return True
            ctx = self._context.copy()
            if work_flow_process_record.sale_journal_id:
                ctx.update({'journal_ept': work_flow_process_record.sale_journal_id})
            invoices = self._create_invoices()
            self.validate_invoice_ept(invoices)
            if work_flow_process_record.register_payment:
                self.paid_invoice_ept(invoices)

    def validate_invoice_ept(self, invoices):
        """
        This method will validate and paid invoices.
        @param invoices: Recordset of Invoice.
        Migration done by Haresh Mori on September 2021
        """
        self.ensure_one()
        for invoice in invoices:
            invoice.action_post()
        return True

    def paid_invoice_ept(self, invoices):
        """
        This method auto paid invoice based on auto workflow method.
        @author: Dipesh Tanna
        @param invoices: Recordset of Invoice.
        Migration done by Haresh Mori on September 2021
        """
        self.ensure_one()
        account_payment_obj = self.env['account.payment']
        for invoice in invoices:
            if invoice.amount_residual:
                vals = invoice.prepare_payment_dict(self.auto_workflow_process_id)
                payment_id = account_payment_obj.create(vals)
                payment_id.action_post()
                self.reconcile_payment_ept(payment_id, invoice)
        return True

    def reconcile_payment_ept(self, payment_id, invoice):
        """ This method is use to reconcile payment.
            @author: twinkalc.
            Migration done by Haresh Mori on September 2021
        """
        move_line_obj = self.env['account.move.line']
        domain = [('account_internal_type', 'in', ('receivable', 'payable')),
                  ('reconciled', '=', False)]
        line_ids = move_line_obj.search([('move_id', '=', invoice.id)])
        to_reconcile = [line_ids.filtered( \
            lambda line: line.account_internal_type == 'receivable')]

        for payment, lines in zip([payment_id], to_reconcile):
            payment_lines = payment.line_ids.filtered_domain(domain)
            for account in payment_lines.account_id:
                (payment_lines + lines).filtered_domain([('account_id', '=', account.id),
                                                         ('reconciled', '=', False)]).reconcile()

    def auto_shipped_order_ept(self, customers_location, is_mrp_installed=False):
        """
        This method is used to create a stock move of shipped orders.
        :param customers_location: It is customer location object.
        :param is_mrp_installed: It is a boolean for mrp installed or not.
        Migration done by Haresh Mori on September 2021
        """
        order_lines = self.order_line.filtered(lambda l: l.product_id.type != 'service')
        vendor_location = self.env['stock.location'].search(['|', ('company_id', '=', self.company_id.id),
                                                             ('company_id', '=', False), ('usage', '=', 'supplier')],
                                                            limit=1)
        for order_line in order_lines:
            bom_lines = []
            if is_mrp_installed:
                bom_lines = self.check_for_bom_product(order_line.product_id)
            for bom_line in bom_lines:
                self.create_and_done_stock_move_ept(order_line, customers_location, bom_line=bom_line)
            if not bom_lines and order_line.product_id.is_drop_ship_product:
                self.create_and_done_stock_move_ept(order_line, customers_location, vendor_location=vendor_location)
            elif not bom_lines or not is_mrp_installed:
                self.create_and_done_stock_move_ept(order_line, customers_location)
        return True

    def check_for_bom_product(self, product):
        """
        Find BOM for phantom type only if Bill of Material type is Make to Order then for shipment report there are
        no logic to create Manufacturer Order.
        Author: Twinkalc
        :param product: Record of Product.
        Migration done by Haresh Mori on September 2021
        """
        try:
            bom_obj = self.env['mrp.bom']
            bom_point_dict = bom_obj.sudo()._bom_find(products=product, company_id=self.company_id.id,
                                                      bom_type='phantom')
            if product in bom_point_dict:
                bom_point = bom_point_dict[product]
                from_uom = product.uom_id
                to_uom = bom_point.product_uom_id
                factor = from_uom._compute_quantity(1, to_uom) / bom_point.product_qty
                bom, lines = bom_point.explode(product, factor, picking_type=bom_point.picking_type_id)
                return lines
        except Exception as error:
            _logger.info("Error when BOM product exlode: %s", error)
        return {}

    def create_and_done_stock_move_ept(self, order_line, customers_location, bom_line=False, vendor_location=False):
        """
        It will create and done stock move as per the data in order line.
        @param customers_location: Customer type location.
        @param order_line: Record of sale order line.
        Migration done by Haresh Mori on September 2021
        """
        if bom_line:
            product = bom_line[0].product_id
            product_qty = bom_line[1].get('qty', 0) * order_line.product_uom_qty
            product_uom = bom_line[0].product_uom_id
        else:
            product = order_line.product_id
            product_qty = order_line.product_uom_qty
            product_uom = order_line.product_uom

        if product and product_qty and product_uom:
            vals = self.prepare_val_for_stock_move_ept(product, product_qty, product_uom, vendor_location,
                                                       customers_location, order_line, bom_line)
            stock_move = self.env['stock.move'].create(vals)
            stock_move._action_assign()
            stock_move._set_quantity_done(product_qty)
            stock_move._action_done()
        return True

    def prepare_val_for_stock_move_ept(self, product, product_qty, product_uom, vendor_location, customers_location,
                                       order_line, bom_line):
        """ This method is used to prepare vals for the stock move.
            @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 21 September 2021 .
            Task_id: 178058
        """
        vals = {
            'name': _('Auto processed move : %s') % product.display_name,
            'company_id': self.company_id.id,
            'product_id': product.id if product else False,
            'product_uom_qty': product_qty,
            'product_uom': product_uom.id if product_uom else False,
            'location_id': vendor_location.id if vendor_location else self.warehouse_id.lot_stock_id.id,
            'location_dest_id': customers_location.id,
            'state': 'confirmed',
            'sale_line_id': order_line.id
        }
        if bom_line:
            vals.update({'bom_line_id': bom_line[0].id})
        return vals
