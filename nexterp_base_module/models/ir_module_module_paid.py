# Copyright 2021 NextERP Romania SRL
# License OPL-1.0 or later
# (https://www.odoo.com/documentation/user/15.0/legal/licenses/licenses.html#).

import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)

PAID_STATES = [
    ("not_paid", "Not Paid"),
    ("subscribed", "Subscribed"),
    ("paid", "Paid"),
    ("blocked", "Blocked"),
]


class IrModulePaid(models.Model):
    _name = "ir.module.module.paid"
    _description = "Partner Paid Module"

    company_id = fields.Many2one(
        "res.company", required=True, default=lambda self: self.env.company
    )
    module_id = fields.Many2one(
        "ir.module.module", string="Module", required=True, ondelete="cascade"
    )
    module_name = fields.Char(
        string="Module Name", related="module_id.name", store=True
    )
    module_state = fields.Selection(
        string="Installation State", related="module_id.state", store=True
    )
    module_extra_buy = fields.Boolean(
        string="Odoo Paid Module", related="module_id.extra_buy", store=True
    )
    paid_state = fields.Selection(
        PAID_STATES, string="Pay Status", default="not_paid", readonly=True, index=True
    )
