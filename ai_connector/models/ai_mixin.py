# Copyright (C) 2024 - Michel Perrocheau (https://github.com/myrrkel).
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.tools.safe_eval import safe_eval
from odoo.addons.base.models.ir_model import SAFE_EVAL_BASE
from odoo.tools import html2plaintext
import logging

_logger = logging.getLogger(__name__)


class AIMixin(models.AbstractModel):
    _name = 'ai.mixin'
    _description = 'AI Mixin'
    _inherit = ['mail.render.mixin']

    name = fields.Char()
    active = fields.Boolean(default=True)
    ai_provider_id = fields.Many2one('ai.provider', string='AI Provider', required=False, ondelete='cascade',
                                     default=lambda self: self.env['ai.provider'].search([], limit=1))
    ai_model_id = fields.Many2one('ai.model', string='AI Model', ondelete='cascade',
                                  default=lambda self: self.env['ai.model'].search([], limit=1))
    ai_provider = fields.Selection(string='AI Provider Code', related='ai_provider_id.code')
    model_id = fields.Many2one('ir.model', string='Model', required=True, ondelete='cascade')
    domain = fields.Char()
    save_on_target_field = fields.Boolean()
    save_answer = fields.Boolean()
    target_field_id = fields.Many2one('ir.model.fields', string='Target Field')
    prompt_template = fields.Text()
    prompt_template_id = fields.Many2one('ir.ui.view', string='Prompt Template View')
    answer_lang_id = fields.Many2one('res.lang', string='Answer Language', context={'active_test': False})
    test_prompt = fields.Text(readonly=True)

    def get_ai_model_list(self):
        if self.ai_provider_id:
            return self.ai_provider_id.get_ai_model_list()
        return []

    @api.onchange('ai_provider_id')
    def _onchange_ai_provider_id(self):
        if not self.ai_provider_id or self.ai_model_id not in self.ai_provider_id.ai_model_ids:
            self.ai_model_id = False
        return {'domain': {'ai_model_id': [('ai_provider_id', '=', self.ai_provider_id.id)]}}


    def get_ai_client(self):
        return self.ai_provider_id.get_ai_client()

    def get_prompt(self, rec_id=0):
        context = {'html2plaintext': html2plaintext}
        lang = self.env.lang
        answer_lang_id = self.answer_lang_id or self.env['res.lang']._lang_get(lang)
        if answer_lang_id:
            context['answer_lang'] = answer_lang_id.name
        if not self.prompt_template_id and not self.prompt_template:
            raise UserError(_('A prompt template is required'))
        return self._get_prompt(rec_id, self.prompt_template_id, self.prompt_template, context)

    def _get_prompt(self, rec_id, prompt_template_id, prompt_template, context=None):
        if not context:
            context = {}
        if prompt_template_id:
            prompt = self._render_template_qweb_view(prompt_template_id.xml_id, self.model_id.model, [rec_id],
                                                     add_context=context)
        elif prompt_template:
            prompt = self._render_template_qweb(prompt_template, self.model_id.model, [rec_id],
                                                add_context=context)
        else:
            return ''

        return prompt[rec_id].strip()

    def get_records(self, limit=0):
        domain = safe_eval(self.domain, SAFE_EVAL_BASE, {'self': self}) if self.domain else []
        rec_ids = self.env[self.model_id.model].search(domain, limit=limit)
        return rec_ids

    def get_record(self, rec_id):
        record_id = self.env[self.model_id.model].browse(rec_id)
        return record_id

    def run(self):
        for rec_id in self.get_records():
            self.apply(rec_id.id)

    def apply(self, rec_id, method=False):
        result_ids = self.ai_create(rec_id, method)
        for result_id in result_ids:
            if self.save_on_target_field:
                result_id.save_result_on_target_field()

    def ai_create(self, rec_id, method=False):
        return []

    def run_test_prompt(self):
        rec_id = self.get_records(limit=1).id
        if not rec_id:
            return
        self.test_prompt = self.get_prompt(rec_id)
