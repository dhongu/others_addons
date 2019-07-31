# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
import werkzeug.urls
from odoo.exceptions import AccessError


class ResCompany(models.Model):
    _inherit = "res.company"

    sale_discount_product_id = fields.Many2one('product.product', string='Sale Discount Product')
    discount_percentage_max = fields.Float("Discount Percentage Max")


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    sale_discount_product_id = fields.Many2one('product.product', string='Sale Discount Product')
    discount_percentage_max = fields.Float("Discount Percentage Max")

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        res.update(
            sale_discount_product_id=self.env.user.company_id.sale_discount_product_id and self.env.user.company_id.sale_discount_product_id.id or False,
            discount_percentage_max=self.env.user.company_id.discount_percentage_max
        )
        return res

    @api.multi
    def set_values(self):
        super(ResConfigSettings, self).set_values()
        if not self.env.user._is_admin():
            raise AccessError(_("Only administrators can change the settings"))

        self.env.user.company_id.write({
            'sale_discount_product_id': self.sale_discount_product_id.id,
            'discount_percentage_max': self.discount_percentage_max,
        })
