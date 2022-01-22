# -*- coding: utf-8 -*-
# Part of AppJetty. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.http import request
from odoo.addons.website_sale.controllers.main import WebsiteSale


class WebsiteSale(WebsiteSale):

    """Add Customer comment functions to the website_sale controller."""
    @http.route(['/shop/customer_comment'], type='json', auth="public", methods=['POST'], website=True)
    def customer_comment(self, **post):
        """ Json method that used to add a
        comment when the user clicks on 'pay now' button.
        """

        if post.get('comment'):
            order = request.website.sale_get_order()
            redirection = self.checkout_redirection(order)
            if redirection:
                return redirection

            if order and order.id:
                order.write({'customer_comment': post.get('comment')})

        return True
