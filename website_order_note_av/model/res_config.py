# -*- coding: utf-8 -*-
from odoo import api, fields, models

class ResConfigSettings(models.TransientModel):

    _inherit = 'res.config.settings'

    enable_order_note = fields.Boolean(string='Enable Order Note',related='website_id.enable_order_note',readonly=False,
                                       help="Enable the order note")
