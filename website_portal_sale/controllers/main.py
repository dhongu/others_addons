# -*- coding: utf-8 -*-
import datetime

from openerp import http
from openerp.exceptions import AccessError
from openerp.http import request

from openerp.addons.website_portal.controllers.main import website_account


class website_account(website_account):
    @http.route(['/my/home'], type='http', auth="user", website=True)
    def account(self, **kw):
        """ Add sales documents to main account page """
        response = super(website_account, self).account()
        partner = request.env.user.partner_id

        res_sale_order = request.env['sale.order']
        res_invoices = request.env['account.invoice']
        quotations = res_sale_order.search([
            ('message_follower_ids', 'child_of', [partner.commercial_partner_id.id]),
            ('state', 'in', ['sent', 'cancel'])
        ])
        orders = res_sale_order.search([
            ('message_follower_ids', 'child_of', [partner.commercial_partner_id.id]),
            ('state', 'not in', ['sent', 'cancel'])
        ])
        invoices = res_invoices.search([
            ('message_follower_ids', 'child_of', [partner.commercial_partner_id.id]),
            ('state', 'in', ['open', 'paid', 'cancel'])
        ])

        response.qcontext.update({
            'date': datetime.date.today().strftime('%Y-%m-%d'),
            'quotations': quotations,
            'orders': orders,
            'invoices': invoices,
        })
        return response

    @http.route(['/my/orders/<int:order>'], type='http', auth="user", website=True)
    def orders_followup(self, order=None):
        order = request.env['sale.order'].browse([order])
        try:
            order.check_access_rights('read')
            order.check_access_rule('read')
        except AccessError:
                return request.website.render("website.403")
        order_invoice_lines = {il.product_id.id: il.invoice_id for il in order.invoice_ids.mapped('invoice_line')}
        return request.website.render("website_portal_sale.orders_followup", {
            'order': order.sudo(),
            'order_invoice_lines': order_invoice_lines,
        })


    @http.route(['/my/invoices', '/my/invoices/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_invoices(self, page=1, date_begin=None, date_end=None, **kw):
        values = self._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        AccountInvoice = request.env['account.invoice']

        domain = [
            ('type', 'in', ['out_invoice', 'out_refund']),
            ('message_partner_ids', 'child_of', [partner.commercial_partner_id.id]),
            ('state', 'in', ['open', 'paid', 'cancel'])
        ]
        archive_groups = self._get_archive_groups('account.invoice', domain)
        if date_begin and date_end:
            domain += [('create_date', '>', date_begin), ('create_date', '<=', date_end)]

        # count for pager
        invoice_count = AccountInvoice.search_count(domain)
        # pager
        pager = request.website.pager(
            url="/my/invoices",
            url_args={'date_begin': date_begin, 'date_end': date_end},
            total=invoice_count,
            page=page,
            step=self._items_per_page
        )
        # content according to pager and archive selected
        invoices = AccountInvoice.search(domain, limit=self._items_per_page, offset=pager['offset'])
        values.update({
            'date': date_begin,
            'invoices': invoices,
            'page_name': 'invoice',
            'pager': pager,
            'archive_groups': archive_groups,
            'default_url': '/my/invoices',
        })
        return request.render("website_portal_sale.portal_my_invoices", values)

    @http.route(['/my/invoices/pdf/<int:invoice_id>'], type='http', auth="user", website=True)
    def portal_get_invoice(self, invoice_id=None, **kw):
        invoice = request.env['account.invoice'].browse([invoice_id])
        try:
            invoice.check_access_rights('read')
            invoice.check_access_rule('read')
        except AccessError:
            return request.render("website.403")



        pdf = request.env['report'].sudo().get_pdf(invoice, 'account.report_invoice')
        pdfhttpheaders = [
            ('Content-Type', 'application/pdf'), ('Content-Length', len(pdf)),
            ('Content-Disposition', 'attachment; filename=%s.pdf;' % invoice.number)
        ]
        return request.make_response(pdf, headers=pdfhttpheaders)