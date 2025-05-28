# Copyright (C) 2024 - Michel Perrocheau (https://github.com/myrrkel).
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).
from odoo import models, fields, api, _
import logging

_logger = logging.getLogger(__name__)


class CreateQuestionAnswerWizard(models.TransientModel):
    _name = 'create.question.answer.wizard'
    _description = "Create Question Answer Wizard"
    completion_result_ids = fields.Many2many('ai.completion.result', string='Completion Results',
                                             default=lambda self: self.env.context.get('active_ids', []))
    answer_type = fields.Selection([('answer', 'Answer'), ('original', 'Original')],
                                   string='Answer Type', default='answer')
    tag_ids = fields.Many2many('ai.question.answer.tag', string='Tags')

    def create_question_answer(self):
        for rec in self:
            for completion_result_id in rec.completion_result_ids:
                completion_result_id.create_question_answer(self.answer_type, rec.tag_ids)
        return {'type': 'ir.actions.act_window_close'}
