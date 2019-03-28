# Copyright 2018 Roel Adriaans <roel@road-support.nl>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class AccountInvoice(models.Model):
    _inherit = "account.invoice"

    invoice_mailed = fields.Boolean("Is Mailed", readonly=True,
                                    default=False, copy=False,
                                    help="It indicates that the "
                                         "invoice has been mailed.")
