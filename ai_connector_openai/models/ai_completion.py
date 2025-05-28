# Copyright (C) 2024 - Michel Perrocheau (https://github.com/myrrkel).
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).

from odoo import models, fields, api, _
import logging

_logger = logging.getLogger(__name__)


class AICompletion(models.Model):
    _inherit = 'ai.completion'

    n = fields.Integer(string='Number of results', default=1)
    stop = fields.Char()
    frequency_penalty = fields.Float()
    presence_penalty = fields.Float()

    def prepare_messages(self, messages):
        return super(AICompletion, self).prepare_messages(messages)

    def get_completion_params(self, messages, kwargs):
        completion_params = super(AICompletion, self).get_completion_params(messages, kwargs)
        if not self.ai_provider == 'openai':
            return completion_params

        stop = kwargs.get('stop', self.stop or '')
        if isinstance(stop, str) and ',' in stop:
            stop = stop.split(',')
        response_format = {'type': kwargs.get('response_format', self.response_format) or 'text'}
        params = {
            'n': self.n or 1,
            'frequency_penalty': self.frequency_penalty,
            'presence_penalty': self.presence_penalty,
            'stop': stop or None,
            'response_format': response_format
        }
        if self.tool_ids:
            params.update({'tools': [t.get_tool_dict() for t in self.tool_ids],
                           'tool_choice': 'auto'})
        completion_params.update(params)
        return completion_params

    def get_completion(self, completion_params):
        if not self.ai_provider == 'openai':
            return super(AICompletion, self).get_completion(completion_params)
        ai_client = self.get_ai_client()
        return ai_client.chat.completions.create(**completion_params)
