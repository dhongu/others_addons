# Copyright (C) 2024 - Michel Perrocheau (https://github.com/myrrkel).
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).
from odoo import models, fields, api, _

import logging

_logger = logging.getLogger(__name__)


class AIModel(models.Model):
    _name = 'ai.model'
    _description = 'AI Model'
    _order = 'ai_provider_sequence, default desc, sequence'
    _rec_name = 'display_name'

    active = fields.Boolean(default=True)
    default = fields.Boolean()
    sequence = fields.Integer()
    name = fields.Char(required=True)
    label = fields.Char()
    display_name = fields.Char(compute='_compute_display_name')
    ai_provider_id = fields.Many2one('ai.provider', string='AI Provider', required=True, index=True, ondelete='cascade')
    ai_provider_sequence = fields.Integer(related='ai_provider_id.sequence', string='AI Provider Sequence',
                                          store=True, index=True)

    @api.depends('name', 'label')
    def _compute_display_name(self):
        for record in self:
            record.display_name = record.label or record.name
