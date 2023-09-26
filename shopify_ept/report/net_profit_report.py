# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ReportAccountFinancialReportExtended(models.Model):
    _inherit = "account.financial.html.report"

    # shopify_instance_id = fields.Many2one("shopify.instance.ept", "Shopify Instance", copy=False,
    #                                       readonly=True)

    def _get_options(self, previous_options=None):
        # OVERRIDE
        options = super(ReportAccountFinancialReportExtended, self)._get_options(previous_options)

        # If manual values were stored in the context, we store them as options.
        # This is useful for report printing, were relying only on the context is
        # not enough, because of the use of a route to download the report (causing
        # a context loss, but keeping the options).
        # if self._context.get('financial_report_line_values'):
        #     options['financial_report_line_values'] = self.env.context['financial_report_line_values']
        if self._context.get('shopify_report'):
            shopify_instance_id = self.env['shopify.instance.ept'].search([('active', '=', 'True')])
            options.update({'analytic_accounts': [shopify_instance_id.shopify_analytic_account_id.id]})
        return options
