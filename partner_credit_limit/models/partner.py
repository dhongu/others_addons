# See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    over_credit = fields.Boolean(string='Allow Over Credit?')
    clemency_days = fields.Integer(string="Clemency Days")
