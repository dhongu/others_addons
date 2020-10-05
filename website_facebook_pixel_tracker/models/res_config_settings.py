# -*- coding: utf-8 -*-
from odoo import fields, models, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    @api.depends('website_id')
    def has_facebook_pixel_method(self):
        self.has_facebook_pixel = bool(self.facebook_pixel_code)

    def inverse_has_facebook_pixel(self):
        if not self.has_facebook_pixel:
            self.facebook_pixel_code = False

    facebook_pixel_code = fields.Char(
        related='website_id.facebook_pixel_code',
        readonly=False)
    has_facebook_pixel = fields.Boolean(
        "Facebook Pixel Tracker",
        compute=has_facebook_pixel_method,
        inverse=inverse_has_facebook_pixel)
