# Copyright (C) 2024 - Michel Perrocheau (https://github.com/myrrkel).
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).
from openai import OpenAI
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class AIProvider(models.Model):
    _inherit = 'ai.provider'

    code = fields.Selection(selection_add=[('openai', 'OpenAI')], ondelete={'openai': 'cascade'})

    def get_ai_model_list(self):
        if not self.code == 'openai':
            return super(AIProvider, self).get_ai_model_list()
        try:
            ai_client = self.get_ai_client()
        except Exception as err:
            _logger.error(err)
            return [('gpt-3.5-turbo', 'GPT-3.5 Turbo')]
        model_list = ai_client.models.list()
        res = [(m.id, m.id) for m in model_list.data]
        res.sort()
        return res

    def get_ai_client(self):
        if not self.code == 'openai':
            return super(AIProvider, self).get_ai_client()
        if not self.api_key:
            raise UserError(_('OpenAI API key is required.'))
        client = OpenAI(api_key=self.api_key, base_url=self.base_url or None)
        return client
