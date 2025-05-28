# Copyright (C) 2024 - Michel Perrocheau (https://github.com/myrrkel).
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).

from odoo import models, fields, api, _

import logging

_logger = logging.getLogger(__name__)


class AITool(models.Model):
    _name = 'ai.tool'
    _description = 'AI Tool'

    def _get_tool_type_list(self):
        return [('function', _('Function'))]

    name = fields.Char()
    description = fields.Text()
    model_id = fields.Many2one('ir.model', string='Model', ondelete='cascade')
    model = fields.Char(related='model_id.model', string='Model Name', readonly=True, store=True)
    type = fields.Selection(selection=_get_tool_type_list)
    property_ids = fields.One2many('ai.tool.property', 'tool_id', string='Properties', copy=True)
    required_property_ids = fields.One2many('ai.tool.property', 'tool_id', string='Required Properties',
                                            domain=[('required', '=', True)], readonly=True)

    def get_tool_dict(self):
        res = {'type': 'function',
               'function': {
                   'name': self.name,
                   'description': self.description}}
        properties = {}
        for property_id in self.property_ids:
            properties[property_id.name] = {'type': property_id.type,
                                            'description': property_id.description}
        if properties:
            parameters = {'type': 'object',
                          'properties': properties}
            required = [p.name for p in self.required_property_ids]
            if required:
                parameters['required'] = required
            res['function']['parameters'] = parameters
        return res
