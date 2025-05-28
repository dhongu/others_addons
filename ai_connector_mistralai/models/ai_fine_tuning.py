# Copyright (C) 2024 - Michel Perrocheau (https://github.com/myrrkel).
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import models, fields, api, _

import logging

_logger = logging.getLogger(__name__)


class AIFineTuning(models.Model):
    _inherit = 'ai.fine.tuning'

    def get_create_fine_tuning_job_params(self):
        res = super(AIFineTuning, self).get_create_fine_tuning_job_params()
        if self.ai_provider == 'mistralai':
            res['hyperparameters'] = {'training_steps': self.training_steps,
                                      'learning_rate': self.learning_rate}
            return res
