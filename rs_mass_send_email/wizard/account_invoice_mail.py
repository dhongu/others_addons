# Copyright 2018 Roel Adriaans <roel@road-support.nl>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models, fields, _
from odoo.exceptions import UserError, ValidationError


class AccountInvoiceMail(models.TransientModel):
    """
    Mail selected invoices
    """

    _name = "account.invoice.mail"
    _description = "Mail selected invoices"

    mail_template = fields.Many2one(
        'mail.template', string="Email Template", required=True,
        default=lambda self: self.env.ref(
            'account.email_template_edi_invoice', False
        ),
        domain=[('model', '=', 'account.invoice')]
    )

    @api.multi
    def invoice_send(self):
        context = dict(self._context or {})
        active_ids = context.get('active_ids', []) or []
        if not self.mail_template:
            raise ValidationError(_('Email template is not selected'))

        # Validate the invoices, onl
        for record in self.env['account.invoice'].browse(active_ids):
            if record.state in ('draft', 'cancel', 'proforma2'):
                raise UserError(_(
                    "Selected invoice(s) cannot be send as they are in "
                    "not in 'Open', 'Sent' or 'Paid' state."))
            if not record.partner_id.email:
                raise UserError(_('Set an email address for the partner %s')
                                % record.partner_id.name)

        template = self.mail_template
        for record in self.env['account.invoice'].browse(active_ids):
            # Compose and send the message.
            record.message_post_with_template(
                template_id=template.id,
                model='account.invoice',
                res_id=record.id,
            )

            record.write({
                'invoice_mailed': True,
                'sent': True,
            })
