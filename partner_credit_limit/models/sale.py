# See LICENSE file for full copyright and licensing details.


import datetime
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DF


class SaleOrder(models.Model):
    _inherit = "sale.order"

    @api.multi
    def check_limit(self):
        self.ensure_one()
        partner = self.partner_id
        moveline_obj = self.env['account.move.line']

        movelines = moveline_obj.search([
            ('partner_id', '=', partner.id),
            ('full_reconcile_id', '=', False),
            ('account_id.internal_type', 'in', ['receivable', 'payable'])
        ])
        debit, credit = 0.0, 0.0
        # today_dt = datetime.strftime(datetime.now().date(), DF)
        today_dt = fields.Date.from_string(fields.Date.today())
        for line in movelines:
            date_maturity = fields.Date.from_string(line.date_maturity) + datetime.timedelta(days=partner.clemency_days)
            if date_maturity < today_dt: # and line.user_type_id.type in ['receivable', 'payable']:
                credit += line.debit
                debit += line.credit

        if partner.credit_limit and ((credit - debit + self.amount_total) > partner.credit_limit):
            if not partner.over_credit:
                msg = _('Credit Over Limits !')
                msg += _('Can not confirm Sale Order.')
                msg += _('Total mature due Amount  %s as on %s !') % (credit - debit, today_dt)
                msg += _('Check Partner Accounts or Credit  Limits')
                raise UserError(msg)
            partner.write({'credit_limit': credit - debit + self.amount_total})
        return True

    @api.multi
    def action_confirm(self):
        res = super(SaleOrder, self).action_confirm()
        for order in self:
            order.check_limit()
        return res
