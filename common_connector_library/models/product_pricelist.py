# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.
from odoo import models


class ProductPricelist(models.Model):
    _inherit = "product.pricelist"

    def get_product_price_ept(self, product, partner=False):
        """ Use to get product price from pricelsit.
            @param product: Record of product variant
            @param product: Record of customer/partner
            @return: Price of product
            @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 23 September 2021 .
            Task_id: 178058
        """
        price = self.get_product_price(product, 1.0, partner=partner, uom_id=product.uom_id.id)
        return price

    def set_product_price_ept(self, product_id, price, min_qty=1):
        """ Use to Create/Update price in the pricelist.
            @param product_id: Record of product
            @param price: Price of Product.
            @return: Record of pricelist item.
            @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 23 September 2021 .
            Task_id: 178058
        """
        pricelist_item_obj = self.env['product.pricelist.item']
        domain = [('pricelist_id', '=', self.id), ('product_id', '=', product_id), ('min_quantity', '=', min_qty)]

        pricelist_item = pricelist_item_obj.search(domain)

        if pricelist_item:
            pricelist_item.write({'fixed_price': price})
        else:
            vals = self.prepre_pricelistitem_vals(product_id, min_qty, price)
            new_record = pricelist_item_obj.new(vals)
            new_record._onchange_product_id()
            new_vals = pricelist_item_obj._convert_to_write(
                {name: new_record[name] for name in new_record._cache})
            pricelist_item = pricelist_item_obj.create(new_vals)
        return pricelist_item

    def prepre_pricelistitem_vals(self, product_id, min_qty, price):
        """ Use to preapre a vals of pricelist item.
            @return: Vals of pricelist item.
            @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 23 September 2021 .
            Task_id: 178058
        """
        vals = {
            'pricelist_id': self.id,
            'applied_on': '0_product_variant',
            'product_id': product_id,
            'min_quantity': min_qty,
            'fixed_price': price,
        }
        return vals
