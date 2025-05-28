# Copyright (C) 2024 - Michel Perrocheau (https://github.com/myrrkel).
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).
from odoo import models, fields, api, _

import logging

from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class AIProvider(models.Model):
    _name = 'ai.provider'
    _description = 'AI Provider'
    _order = 'sequence'

    active = fields.Boolean(default=True)
    sequence = fields.Integer()
    name = fields.Char(required=True)
    code = fields.Selection(selection=[('odoo', 'Odoo')], required=True)
    api_key = fields.Char()
    organization_id = fields.Char(string='Organization ID')
    ai_model_ids = fields.One2many('ai.model', 'ai_provider_id', string='AI Models', readonly=True)
    base_url = fields.Char()

    def get_ai_model_list(self):
        return []

    def get_ai_client(self):
        raise UserError(_('No AI provider found'))

    def action_load_ai_models(self):
        ai_models = self.get_ai_model_list()
        for ai_model in ai_models:
            ai_model_id = self.env['ai.model'].search([('name', '=', ai_model[0]),
                                                       ('ai_provider_id', '=', self.id)], limit=1)
            if not ai_model_id:
                values = {'name': ai_model[0],
                          'display_name': ai_model[1],
                          'ai_provider_id': self.id}
                self.env['ai.model'].create(values)
        deprecated_model_ids = self.env['ai.model'].search([('name', 'not in', [m[0] for m in ai_models]),
                                                            ('ai_provider_id', '=', self.id)])
        deprecated_model_ids.write({'active': False})
