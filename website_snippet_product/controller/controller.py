# -*- coding: utf-8 -*-
import json
import openerp
import openerp.addons.website_sale.controllers.main
from openerp.addons.website.models.website import slug
from openerp.addons.website_sale.controllers.main import QueryURL
from openerp.addons.web import http
from openerp.addons.web.http import request
from openerp.tools.translate import _
from openerp.osv import osv


class my_snippet(openerp.addons.website_sale.controllers.main.website_sale):
    @http.route(['/get_product_list'], type='json', auth="public", website=True)
    def get_prod_top2(self, mode, max_item, lang):
        cr, uid, context, pool = request.cr, request.uid, request.context, request.registry

        context["lang"] = lang  # forcing lang
        pricelist = self.get_pricelist()
        if not context.get('pricelist'):
            context['pricelist'] = int(self.get_pricelist())

        from_currency = pool.get('product.price.type')._get_field_currency(cr, uid, 'list_price', context)
        to_currency = pricelist.currency_id

        # default = lasted update
        requete = [('website_published', '=', True), ('image', '!=', 'null')]
        order = 'write_date desc'

        # <option value="top_sales"> = top des ventes

        if mode == "top_sales":
            cr.execute("select product_tmpl_id from product_product where id in ("
                       "select product_id from "
                       "sale_order_line where state=%s "
                       "group by product_id order by count(product_id) desc "
                       "limit (%s));", ("confirmed", max_item,))
            results = cr.fetchall()

            list_id = []
            for res in results:
                list_id.append(res[0])

            requete = [('website_published', '=', True), ('image', '!=', 'null'), ('id', 'in', list_id)]

        # <option value="last_sales" = derniere ventes
        if mode == "last_sales":
            results = http.request.env['sale.order.line'].sudo().search([("state", "=", "confirmed")], limit=max_item,
                                                                        order="create_date desc")
            list_id = []
            for res in results:
                list_id.append(res.product_id.product_tmpl_id.id)

            requete = [('website_published', '=', True), ('image', '!=', 'null'), ('id', 'in', list_id)]

        # only_new
        if mode == "only_new":
            order = 'create_date desc'

        # only_sale
        if mode == "only_sale":
            style_id = http.request.env['product.style'].search([('html_class', '=', 'oe_ribbon_promo')]).read(['id'])
            requete = [('website_published', '=', True), ('image', '!=', 'null'),
                       ('website_style_ids', 'in', style_id[0]['id'])]
            order = 'create_date desc'

        compute_currency = lambda price: pool['res.currency']._compute(cr, uid, from_currency, to_currency, price,
                                                                       context=context)

        list_prods = http.request.env['product.template'].search(requete, limit=max_item,  order=order).read(['id'])
        html = []
        keep = QueryURL('/shop', category='' and int(0), search='', attrib='')

        for prod in list_prods:
            product = http.request.env['product.template'].with_context(context).browse(  prod['id']  )
            list_style = 'oe_product oe_grid oe-height-2'
            for style_ids in product.read(['website_style_ids']):
                for style_id in style_ids['website_style_ids']:
                    style = http.request.env['product.style'].search([('id', '=', style_id)]).read()[0]
                    list_style = '%s %s' % (list_style, style['html_class'])

            context.update(active_id=product.id)


            values = {
                'compute_currency': compute_currency,
                'pager': {'page': {'num': 1}},
                'keep': keep,
                'style_in_product': list_style,
                'product': product,
                'pricelist': pricelist,
            }

            valhtml = request.website._render('website_snippet_product.product', values)

            html.append(valhtml)
        return html
