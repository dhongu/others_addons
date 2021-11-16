# -*- coding: utf-8 -*-
from odoo import api, fields, models

class Website(models.Model):
    _inherit = 'website'

    enable_order_note = fields.Boolean(string='Enable Order Note', help="Enable the order note")
