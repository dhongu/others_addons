# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.

from odoo import models

class StockMove(models.Model):
    """Inherit model to set the instance and is shopify delivery order flag"""
    _inherit = "stock.move"

    def _get_new_picking_values(self):
        """We need this method to set Shopify Instance in Stock Picking"""
        res = super(StockMove, self)._get_new_picking_values()
        order_id = self.sale_line_id.order_id
        if order_id.shopify_order_id:
            res.update({'shopify_instance_id': order_id.shopify_instance_id.id, 'is_shopify_delivery_order': True})
        return res

    def _action_assign(self):
        # We inherited the base method here to set the instance values in picking while the picking type is dropship.
        res = super(StockMove, self)._action_assign()

        for picking in self.picking_id:
            if not picking.shopify_instance_id and picking.sale_id and picking.sale_id.shopify_instance_id:
                picking.write({'shopify_instance_id':picking.sale_id.shopify_instance_id.id})
        return res
