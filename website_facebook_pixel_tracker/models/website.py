# -*- coding: utf-8 -*-
from odoo import models, fields


class Website(models.Model):

    _inherit = "website"
    facebook_pixel_code = fields.Char()
