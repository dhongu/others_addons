# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.
from odoo import models, api


class AccountMove(models.Model):
    _inherit = 'account.move'

    @api.model
    def _get_default_journal(self):
        res = super(AccountMove, self)._get_default_journal()
        if self._context.get('journal_ept'):
            res = self._context.get('journal_ept')
        return res

    def prepare_payment_dict(self, work_flow_process_record):
        """ This method use to prepare a vals dictionary for payment.
            @param work_flow_process_record: Record of auto invoice workflow.
            @return: Dictionary of payment vals
            @author: Twinkalc.
            Migration done by Haresh Mori on September 2021
        """
        return {
            'journal_id': work_flow_process_record.journal_id.id,
            'ref': self.payment_reference,
            'currency_id': self.currency_id.id,
            'payment_type': 'inbound',
            'date': self.date,
            'partner_id': self.commercial_partner_id.id,
            'amount': self.amount_residual,
            'payment_method_id': work_flow_process_record.inbound_payment_method_id.id,
            'partner_type': 'customer'
        }
