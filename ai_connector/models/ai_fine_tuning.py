# Copyright (C) 2024 - Michel Perrocheau (https://github.com/myrrkel).
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import json
from odoo import models, fields, api, _
from odoo.tools.safe_eval import safe_eval
from odoo.addons.base.models.ir_model import SAFE_EVAL_BASE

import logging

_logger = logging.getLogger(__name__)


class AIFineTuning(models.Model):
    _name = 'ai.fine.tuning'
    _description = 'AI Fine-Tuning'

    name = fields.Char()
    ai_provider_id = fields.Many2one('ai.provider', string='AI Provider', required=True, ondelete='cascade',
                                     default=lambda self: self.env['ai.provider'].search([], limit=1))
    ai_model_id = fields.Many2one('ai.model', string='AI Model', required=True, ondelete='cascade',
                                  default=lambda self: self.env['ai.model'].search([], limit=1))
    ai_provider = fields.Selection(string='AI Provider Code', related='ai_provider_id.code')
    training_steps = fields.Integer(default=10)
    learning_rate = fields.Float(default=0.0001, digits=(10, 7))
    training_file_id = fields.Char('Training File ID', readonly=True, copy=False)
    fine_tuning_job_id = fields.Char('Fine-Tuning Job ID', readonly=True, copy=False)
    fine_tuned_model = fields.Char('Fine-Tuned Model', readonly=True, copy=False)
    question_answer_domain = fields.Char()
    question_answer_tag_ids = fields.Many2many('ai.question.answer.tag', string='Tags')
    question_answer_ids = fields.Many2many('ai.question.answer', string='Questions - Answers',
                                           compute='_compute_question_answers',
                                           store=False)
    training_question_answer_ids = fields.Many2many('ai.question.answer',
                                                    string='Training Questions - Answers',
                                                    store=True, readonly=True, copy=False)
    system_role_content = fields.Char()
    job_status = fields.Char(readonly=True, copy=False)
    fine_tuning_checkpoints = fields.Json(copy=False)
    graph_checkpoints = fields.Json(compute='_compute_graph_checkpoints', store=False)

    def get_ai_client(self):
        return self.ai_provider_id.get_ai_client()

    def get_fine_tuning_job_client(self):
        client = self.get_ai_client()
        return client.fine_tuning.jobs

    @api.onchange('question_answer_tag_ids', 'question_answer_domain')
    def _compute_question_answers(self):
        for rec in self:
            domain = safe_eval(rec.question_answer_domain,
                               SAFE_EVAL_BASE,
                               {'self': rec}) if rec.question_answer_domain else []
            question_answer_ids = self.env['ai.question.answer'].search(domain)
            question_answer_ids = question_answer_ids.filtered(lambda x: x.tag_ids & rec.question_answer_tag_ids)
            rec.question_answer_ids = question_answer_ids

    @api.depends('fine_tuning_checkpoints')
    def _compute_graph_checkpoints(self):
        for rec in self:
            checkpoints = self.fine_tuning_checkpoints
            if not checkpoints:
                rec.graph_checkpoints = []
                continue
            checkpoints.sort(key=lambda x: x['created_at'])
            train_loss_vals = [x['metrics']['train_loss'] for x in checkpoints]
            valid_loss_vals = [x['metrics']['valid_loss'] for x in checkpoints]
            valid_mean_token_accuracy_vals = [x['metrics']['valid_mean_token_accuracy'] for x in checkpoints]
            graph_values = {'labels': [x['step_number'] for x in checkpoints],
                            'train_loss': train_loss_vals,
                            'valid_loss': valid_loss_vals,
                            'valid_mean_token_accuracy': valid_mean_token_accuracy_vals} if checkpoints else []
            rec.graph_checkpoints = graph_values

    def get_training_content(self):
        content = ''
        for question_answer_id in self.question_answer_ids:
            messages = []
            if self.system_role_content:
                messages.append({'role': 'system', 'content': self.system_role_content})

            messages.extend(question_answer_id.get_training_content())

            values = {'messages': messages}
            content += json.dumps(values) + '\n'
        return bytes(content, 'utf-8')

    def create_training_file(self):
        client = self.get_ai_client()
        file = ('training_%s' % self.id, self.get_training_content())
        res = client.files.create(file=file, purpose='fine-tune')
        self.training_file_id = res.id
        self.training_question_answer_ids = self.question_answer_ids

    def get_create_fine_tuning_job_params(self):
        return {
            'training_file': self.training_file_id,
            'model': self.ai_model_id.name
        }

    def create_fine_tuning(self):
        jobs = self.get_fine_tuning_job_client()
        params = self.get_create_fine_tuning_job_params()
        res = jobs.create(**params)
        self.fine_tuning_job_id = res.id
        _logger.info(res)

    def update_fine_tuned_model(self):
        jobs = self.get_fine_tuning_job_client()
        res = jobs.retrieve(self.fine_tuning_job_id)
    #     checkpoints = [
    #     {
    #         "metrics": {
    #             "train_loss": 0.816135,
    #             "valid_loss": 0.819697,
    #             "valid_mean_token_accuracy": 1.765035
    #         },
    #         "step_number": 100,
    #         "created_at": 1717173470
    #     },
    #     {
    #         "metrics": {
    #             "train_loss": 0.84643,
    #             "valid_loss": 0.819768,
    #             "valid_mean_token_accuracy": 1.765122
    #         },
    #         "step_number": 90,
    #         "created_at": 1717173388
    #     },
    #     {
    #         "metrics": {
    #             "train_loss": 0.816602,
    #             "valid_loss": 0.820234,
    #             "valid_mean_token_accuracy": 1.765692
    #         },
    #         "step_number": 80,
    #         "created_at": 1717173303
    #     },
    #     {
    #         "metrics": {
    #             "train_loss": 0.775537,
    #             "valid_loss": 0.821105,
    #             "valid_mean_token_accuracy": 1.766759
    #         },
    #         "step_number": 70,
    #         "created_at": 1717173217
    #     },
    #     {
    #         "metrics": {
    #             "train_loss": 0.840297,
    #             "valid_loss": 0.822249,
    #             "valid_mean_token_accuracy": 1.76816
    #         },
    #         "step_number": 60,
    #         "created_at": 1717173131
    #     },
    #     {
    #         "metrics": {
    #             "train_loss": 0.823884,
    #             "valid_loss": 0.824598,
    #             "valid_mean_token_accuracy": 1.771041
    #         },
    #         "step_number": 50,
    #         "created_at": 1717173045
    #     },
    #     {
    #         "metrics": {
    #             "train_loss": 0.786473,
    #             "valid_loss": 0.827982,
    #             "valid_mean_token_accuracy": 1.775201
    #         },
    #         "step_number": 40,
    #         "created_at": 1717172960
    #     },
    #     {
    #         "metrics": {
    #             "train_loss": 0.8704,
    #             "valid_loss": 0.835169,
    #             "valid_mean_token_accuracy": 1.784066
    #         },
    #         "step_number": 30,
    #         "created_at": 1717172874
    #     },
    #     {
    #         "metrics": {
    #             "train_loss": 0.880803,
    #             "valid_loss": 0.852521,
    #             "valid_mean_token_accuracy": 1.805653
    #         },
    #         "step_number": 20,
    #         "created_at": 1717172788
    #     },
    #     {
    #         "metrics": {
    #             "train_loss": 0.803578,
    #             "valid_loss": 0.914257,
    #             "valid_mean_token_accuracy": 1.884598
    #         },
    #         "step_number": 10,
    #         "created_at": 1717172702
    #     }
    # ]

        self.fine_tuning_checkpoints = [{'step_number': c.step_number, 'created_at': c.created_at, 'metrics': {
            "train_loss": c.metrics.train_loss,
            "valid_loss": c.metrics.valid_loss,
            "valid_mean_token_accuracy": c.metrics.valid_mean_token_accuracy
        }} for c in res.checkpoints]
        if res.status != self.job_status:
            self.job_status = res.status
            if res.status == 'SUCCESS':
                self.fine_tuned_model = res.fine_tuned_model
                self.env['ai.model'].create({'name': self.fine_tuned_model,
                                             'display_name': 'Fine-Tuned - %s' % self.name,
                                             'ai_provider_id': self.ai_provider_id.id})
        _logger.info(res)

    def action_create_training_file(self):
        for rec in self:
            rec.create_training_file()

    def action_create_fine_tuning(self):
        for rec in self:
            if not rec.training_file_id:
                rec.create_training_file()
            rec.create_fine_tuning()

    def action_update_fine_tuned_model(self):
        for rec in self:
            rec.update_fine_tuned_model()
