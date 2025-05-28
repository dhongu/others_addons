# Copyright (C) 2024 - Michel Perrocheau (https://github.com/myrrkel).
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).

from odoo import models, fields, api, _

import logging

_logger = logging.getLogger(__name__)

from random import randint

from odoo import fields, models


class AIQuestionAnswerTag(models.Model):
    _name = 'ai.question.answer.tag'
    _description = "AI Question Answer Tag"

    def _get_default_color(self):
        return randint(1, 11)

    name = fields.Char(required=True)
    color = fields.Integer('Color', default=_get_default_color)

    _sql_constraints = [
        ('name_uniq', 'unique (name)', "Tag name already exists !"),
    ]
