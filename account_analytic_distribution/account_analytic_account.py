# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import models, fields, api, _
from openerp.exceptions import Warning
import logging
_logger = logging.getLogger(__name__)


class AccountAnalyticAccount(models.Model):
    _inherit = "account.analytic.account"

    type = fields.Selection(
        selection_add=[('distribution', 'Distribution')],
        )
    distribution_line_ids = fields.One2many(
        'account.analytic.account.distribution_line',
        'distribution_analytic_id',
        'Distribution Line',
        )

    @api.one
    @api.constrains('distribution_line_ids', 'type')
    def check_distribution_lines(self):
        difference = self.company_id.currency_id.round(sum(
            self.distribution_line_ids.mapped('percentage')) - 100.0)
        if self.type == 'distribution' and difference:
            raise Warning(_(
                'Lines of the analytic distribuion account "%s" must '
                'sum 100') % self.name)


class AccountAnalyticAccountDistribution(models.Model):
    _name = "account.analytic.account.distribution_line"

    distribution_analytic_id = fields.Many2one(
        'account.analytic.account',
        'Distribution Account',
        required=True,
        ondelete='cascade',
        )
    account_analytic_id = fields.Many2one(
        'account.analytic.account',
        'Analytic Account',
        required=True,
        )
    percentage = fields.Float(
        'Percentage',
        required=True,
        )
