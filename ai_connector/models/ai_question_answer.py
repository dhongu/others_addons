# Copyright (C) 2024 - Michel Perrocheau (https://github.com/myrrkel).
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).
import json
from odoo import models, fields, api, _
from odoo.osv import expression
import logging

_logger = logging.getLogger(__name__)


class AIQuestionAnswer(models.Model):
    _name = 'ai.question.answer'
    _description = 'AI Question Answer'
    _order = 'create_date desc'

    name = fields.Text('Question')
    answer = fields.Text('Answer')
    model_id = fields.Many2one('ir.model', string='Model', ondelete='cascade')
    model = fields.Char(related='model_id.model', string='Model Name', readonly=True, store=True)
    res_id = fields.Integer('Resource ID', readonly=True)
    resource_ref = fields.Reference(string='Record', selection='_selection_target_model',
                                    compute='_compute_resource_ref', inverse='_set_resource_ref')
    answer_completion_id = fields.Many2one('ai.completion', string='Answer Completion')
    content_length = fields.Integer(compute='_compute_content_length')
    tag_ids = fields.Many2many('ai.question.answer.tag', string='Tags')

    @api.model
    def _selection_target_model(self):
        model_ids = self.env['ir.model'].search([])
        return [(model.model, model.name) for model in model_ids]

    def _compute_content_length(self):
        for res in self:
            res.content_length = len(res.name) + len(res.answer)

    @api.depends('res_id')
    def _compute_resource_ref(self):
        for rec in self:
            if rec.model_id and rec.res_id:
                record = self.env[rec.model_id.model].browse(rec.res_id)
                res_id = record[0] if record else 0
                rec.resource_ref = '%s,%s' % (rec.model_id.model, res_id.id)
            else:
                rec.resource_ref = False

    @api.onchange('resource_ref')
    def _set_resource_ref(self):
        for rec in self:
            if rec.resource_ref:
                rec.model_id = self.env['ir.model']._get(rec.resource_ref._name)
                rec.res_id = rec.resource_ref.id

    def get_training_content(self):
        return [{'role': 'user', 'content': self.name},
                {'role': 'assistant', 'content': self.answer}]

    def action_answer_question(self):
        for rec in self:
            res = rec.answer_completion_id.create_completion(rec.id, prompt=rec.name)
            rec.answer = res[0].answer

    def get_score(self, keyword_list):
        score = 0
        for keyword in keyword_list:
            keyword = keyword.lower()
            if keyword in self.name.lower():
                score += 2
            if keyword in self.answer.lower():
                score += 1
        return score

    @api.model
    def search_question_answer(self, keywords):
        keyword_list = keywords.replace(' ', ',').replace(';', ',').split(',')
        domain = []
        for keyword in keyword_list:
            domain = expression.OR([domain, [('name', '=ilike', f'%{keyword}%')]])
            domain = expression.OR([domain, [('answer', '=ilike', f'%{keyword}%')]])
        question_answer_ids = self.search(domain)
        if not question_answer_ids:
            return 'No result found. Suggest to user to reformulate his question or to provide more relevant keywords.'
        res = [{'question': q.name,
                'answer': q.answer,
                'score': q.get_score(keyword_list),
                'length': q.content_length,
                }
               for q in question_answer_ids]
        res = sorted(res, key=lambda x: x['score'], reverse=True)
        max_score = res[0]['score']
        res = list(filter(lambda x: x['score'] == max_score, res))
        res = sorted(res, key=lambda x: x['length'])
        return json.dumps(res[0])
