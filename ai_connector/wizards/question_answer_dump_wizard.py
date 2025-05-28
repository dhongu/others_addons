# Copyright (C) 2024 - Michel Perrocheau (https://github.com/myrrkel).
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).
from odoo import models, fields, api, _
import logging

_logger = logging.getLogger(__name__)


class QuestionAnswerDumpWizard(models.TransientModel):
    _name = 'question.answer.dump.wizard'
    _description = "Question Answer Dump Wizard"

    def _default_question_answer_dump(self):
        question_answer_ids = self.env['ai.question.answer'].browse(self.env.context.get('active_ids', []))
        content = ''
        for question_answer_id in question_answer_ids:
            messages = "[\n{'role': 'user', 'content': %s},\n{'role': 'assistant', 'content': %s}]" % (
                question_answer_id.name, question_answer_id.answer)
            content += "{'messages': %s}\n" % messages
        return content

    question_answer_dump = fields.Text(default=_default_question_answer_dump)
