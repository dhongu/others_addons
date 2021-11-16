# -*- coding: utf-8 -*-

from odoo import http
from odoo.http import request
from odoo.addons.website_sale.controllers.main import WebsiteSale


class websiteSaleOrder(WebsiteSale):

    # Set order note
    @http.route(['/order-note'], type='json', auth="public", methods=['POST'], website=True)
    def order_comment(self, **post):
        if post.get('website_order_note'):
            order = request.website.sale_get_order()
            redirection = self.checkout_redirection(order)
            if redirection:
                return redirection

            if order and order.id:
                order.sudo().write({'website_order_note': post.get('website_order_note')})

        return True