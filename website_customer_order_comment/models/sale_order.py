# -*- coding: utf-8 -*-
# Part of AppJetty. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from lxml import etree


class sale_order(models.Model):

    """Adds the fields for options of the customer order comment"""

    _inherit = "sale.order"

    _description = 'Sale Order'

    customer_comment = fields.Text('Customer Order Comment',
                                   default="No comment")

    @api.model
    def fields_view_get(self, view_id=None, view_type=False, toolbar=False, submenu=False):
        res = super(sale_order, self).fields_view_get(view_id=view_id,
                                                      view_type=view_type, toolbar=toolbar, submenu=False)
        if res:
            doc = etree.XML(res['arch'])
            if view_type == 'form':
                is_customer_comment_features = False
                search_websites = self.env['website'].search([('id', '!=', False)])

                for setting in search_websites:
                    if setting.is_customer_comment_features:
                        is_customer_comment_features = True

                res['arch'] = etree.tostring(doc)
        return res
