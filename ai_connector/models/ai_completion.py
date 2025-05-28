# Copyright (C) 2024 - Michel Perrocheau (https://github.com/myrrkel).
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).
import json
from odoo import models, fields, api, _
from odoo.tools import html2plaintext
from odoo.addons.web_editor.controllers.main import Web_Editor

import logging

_logger = logging.getLogger(__name__)


def _extract_json(content):
    start_pos = content.find('{')
    end_post = content.rfind('}') + 1
    res = content[start_pos:end_post]
    try:
        json_res = json.loads(res)
    except json.JSONDecodeError as err:
        if '\\_' in res:
            res = res.replace('\\_', '_')
            return _extract_json(res)
        else:
            _logger.error(err)
            return {}
    return res


class AICompletion(models.Model):
    _name = 'ai.completion'
    _description = 'AI Completion'
    _inherit = ['ai.mixin']

    def _get_post_process_list(self):
        return [('list_to_many2many', _('List to Many2many')),
                ('json_to_questions', _('JSON to questions'))]

    def _get_response_format_list(self):
        return [('text', _('Text')),
                ('json_object', _('JSON Object')),
                ]

    system_template = fields.Text()
    system_template_id = fields.Many2one('ir.ui.view', string='System Template View')
    temperature = fields.Float(default=1)
    max_tokens = fields.Integer(default=10000)
    top_p = fields.Float(default=1)
    test_answer = fields.Text(readonly=True)
    post_process = fields.Selection(selection='_get_post_process_list')
    response_format = fields.Selection(selection='_get_response_format_list', default='text')
    tool_ids = fields.Many2many('ai.tool', string='Tools', copy=True)
    add_completion_action_menu = fields.Boolean()

    def prepare_message(self, message):
        return message

    def prepare_messages(self, messages):
        return [self.prepare_message(message) for message in messages]

    def create_completion(self, rec_id=0, messages=None, prompt='', **kwargs):
        prompt_tokens = 0
        completion_tokens = 0
        total_tokens = 0
        response_format = kwargs.get('response_format', self.response_format) or 'text'
        if not messages:
            messages = []
            system_prompt = self.get_system_prompt(rec_id)
            if system_prompt:
                messages.append({'role': 'system', 'content': system_prompt})

            if not prompt:
                prompt = self.get_prompt(rec_id)
            messages.append({'role': 'user', 'content': prompt})
        messages = self.prepare_messages(messages)
        if not rec_id and self.env.context.get('completion'):
            rec_id = self.env.context.get('completion').get('res_id', 0)
            if isinstance(rec_id, list) and len(rec_id) == 1:
                rec_id = rec_id[0]

        if self.ai_provider == 'odoo':
            res = Web_Editor.generate_text(self, prompt, messages)
            choices = [res]
        else:
            res_choices, prompt_tokens, completion_tokens, total_tokens = self.get_completion_results(rec_id,
                                                                                                      messages,
                                                                                                      **kwargs)
            choices = [choice.message.content for choice in res_choices]
        result_ids = []
        for answer in choices:
            _logger.info(f'Completion result: {answer}')
            if rec_id:
                if self.response_format == 'json_object' or response_format == 'json_object':
                    answer = _extract_json(answer)
                if self.save_answer:
                    result_id = self.create_result(rec_id, prompt, answer, prompt_tokens, completion_tokens, total_tokens)
                    result_ids.append(result_id)
                    continue
                if self.post_process and not self.target_field_id:
                    self.exec_post_process(answer)
                if not self.save_answer and self.target_field_id and self.save_on_target_field:
                    self.env[self.model_id.model].browse(rec_id).write({self.target_field_id.name: answer})
                if not self.save_answer:
                    return answer
            else:
                try:
                    return self.get_result_content(response_format, choices)
                except Exception as err:
                    _logger.error(err, exc_info=True)
        return result_ids

    def get_completion_params(self, messages, kwargs):
        model = self.ai_model_id.name or kwargs.get('model', '')
        temperature = self.temperature or kwargs.get('temperature', 0)
        top_p = self.top_p or kwargs.get('top_p', 0)
        max_tokens = kwargs.get('max_tokens', self.max_tokens or 10000)
        completion_params = {
            'model': model,
            'messages': messages,
            'max_tokens': max_tokens,
            'temperature': temperature,
            'top_p': top_p,
        }
        if self.tool_ids:
            completion_params.update({'tools': [t.get_tool_dict() for t in self.tool_ids]})
        return completion_params

    def get_completion(self, completion_params):
        ai_client = self.get_ai_client()
        return ai_client.chat.complete(**completion_params)

    def get_completion_results(self, rec_id, messages, **kwargs):
        _logger.info(f'Create completion: {messages}')
        completion_params = self.get_completion_params(messages, kwargs)
        res = self.get_completion(completion_params)
        for choice in res.choices:
            if choice.finish_reason == 'tool_calls':
                for tool_call in choice.message.tool_calls:
                    messages.append(choice.message)
                    messages.append(self.prepare_message(self.run_tool_call(tool_call)))
                    return self.get_completion_results(rec_id, messages, **kwargs)
        return res.choices, res.usage.prompt_tokens, res.usage.completion_tokens, res.usage.total_tokens

    def get_result_content(self, response_format, choices):
        if self.response_format == 'json_object' or response_format == 'json_object':
            return [_extract_json(choice) for choice in choices]
        return choices

    def ai_create(self, rec_id, method=False):
        return self.create_completion(rec_id)

    def create_result(self, rec_id, prompt, answer, prompt_tokens, completion_tokens, total_tokens):
        model_id = self.model_id.id
        if self.env.context.get('completion'):
            model = self.env.context.get('completion').get('model', '')
            if model:
                model_id = self.env['ir.model'].search([('model', '=', model)]).id

        values = {'completion_id': self.id,
                  'ai_provider_id': self.ai_provider_id.id,
                  'ai_model_id': self.ai_model_id.id,
                  'model_id': model_id,
                  'target_field_id': self.target_field_id.id,
                  'res_id': rec_id,
                  'prompt': prompt,
                  'answer': answer,
                  'prompt_tokens': prompt_tokens,
                  'completion_tokens': completion_tokens,
                  'total_tokens': total_tokens,
                  }
        result_id = self.env['ai.completion.result'].create(values)
        return result_id

    def run_tool_call(self, tool_call):
        tool_name = tool_call.function.name
        res_dict = {'role': 'tool',
                    "tool_call_id": tool_call.id,
                    'content': '',
                    'name': tool_name}
        tool_id = self.tool_ids.filtered(lambda t: t.name == tool_name)
        if not tool_id:
            return res_dict
        model_name = tool_id.model or self.model_id.model
        model = self.env[model_name]

        if hasattr(model, tool_name):
            function = getattr(model, tool_name)
        else:
            model = self.env['ai.tool']
            if hasattr(model, tool_name):
                function = getattr(model, tool_name)
            else:
                return res_dict

        arguments = tool_call.function.arguments
        if arguments:
            arguments_vals = json.loads(arguments)
            _logger.info(f'Run tool: {tool_name}({arguments_vals})')
            res = function(**arguments_vals)
        else:
            res = function()
            _logger.info(f'Run tool: {tool_name}()')

        res_dict['content'] = str(res)
        return res_dict

    def exec_post_process(self, value):
        if not self.post_process:
            return value
        post_process_function = getattr(self, self.post_process)
        return post_process_function(value)

    def get_system_prompt(self, rec_id):
        context = {'html2plaintext': html2plaintext}
        return self._get_prompt(rec_id, self.system_template_id, self.system_template, context)

    def run_test_completion(self):
        rec_id = self.get_records(limit=1).id
        if not rec_id:
            return
        self.test_prompt = self.get_prompt(rec_id)
        res = self.create_completion(rec_id)
        if res and isinstance(res, list):
            self.test_answer = res[0].answer
        else:
            self.test_answer = res

    @api.model
    def get_model_completions(self, model):
        res = self.sudo().search([('model_id', '=', model), ('add_completion_action_menu', '=', True)])
        return [{'id': r.id, 'name': r.name} for r in res]

    @api.model
    def run_completion(self, completion_id, active_ids):
        completion = self.browse(completion_id)
        for res_id in active_ids:
            completion.create_completion(res_id)
            self.browse(completion_id).create_completion(res_id)
