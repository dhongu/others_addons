# -*- coding: utf-8 -*-

from odoo import fields, models, api
import werkzeug.urls


class ResCompany(models.Model):
    _inherit = "res.company"

    sale_discount_product_id = fields.Many2one('product.product', string='Sale Discount Product')


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    sale_discount_product_id = fields.Many2one('product.product', string='Sale Discount Product')

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        res.update(
            sale_discount_product_id=self.env.user.company_id.sale_discount_product_id and self.env.user.company_id.sale_discount_product_id.id or False,
        )
        return res

    @api.multi
    def set_values(self):
        super(ResConfigSettings, self).set_values()
        if not self.env.user._is_admin():
            raise AccessError(_("Only administrators can change the settings"))

        self.env.user.company_id.sale_discount_product_id = self.sale_discount_product_id.id

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: