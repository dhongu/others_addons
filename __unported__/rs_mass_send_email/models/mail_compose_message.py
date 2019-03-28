# Copyright 2018 Roel Adriaans <roel@road-support.nl>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class MailComposeMessage(models.TransientModel):
    _inherit = 'mail.compose.message'

    @api.multi
    def send_mail(self, auto_commit=False):
        ctx = self._context
        if ctx.get('default_model') == 'account.invoice' and \
                ctx.get('default_res_id') and \
                ctx.get('mark_invoice_as_sent'):
            invoice = self.env['account.invoice'].browse(ctx['default_res_id'])
            if not invoice.sent:
                invoice.invoice_mailed = True
        return super(MailComposeMessage, self).send_mail(
            auto_commit=auto_commit
        )
