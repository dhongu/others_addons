# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class AccountBankStatementLine(models.Model):
    """
    Inherited for adding transaction line id for Shopify Payout Report.
    @author: Maulik Barad on Date 02-Dec-2020.
    """
    _inherit = "account.bank.statement.line"

    shopify_transaction_id = fields.Char("Shopify Transaction")
    shopify_transaction_type = fields.Selection([('charge', 'Charge'), ('refund', 'Refund'), ('dispute', 'Dispute'),
                                                 ('reserve', 'Reserve'), ('adjustment', 'Adjustment'),
                                                 ('credit', 'Credit'),
                                                 ('debit', 'Debit'), ('payout', 'Payout'),
                                                 ('payout_failure', 'Payout Failure'),
                                                 ('payout_cancellation', 'Payout Cancellation'), ('fees', 'Fees'),
                                                 ('payment_refund', 'Payment Refund')],
                                                help="The type of the balance transaction",
                                                string="Balance Transaction Type")
