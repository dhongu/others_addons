# Copyright (C) 2024 - Michel Perrocheau (https://github.com/myrrkel).
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).

from odoo import models, fields, api, _

import logging

_logger = logging.getLogger(__name__)


class AIToolProperty(models.Model):
    _name = 'ai.tool.property'
    _description = 'AI Tool Property'

    def _get_tool_property_type_list(self):
        return [('string', _('String')),
                ('integer', _('Integer'))]

    name = fields.Char()
    tool_id = fields.Many2one('ai.tool')
    type = fields.Selection(selection=_get_tool_property_type_list)
    description = fields.Text()
    required = fields.Boolean()
