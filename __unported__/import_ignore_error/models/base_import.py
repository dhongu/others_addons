# -*- coding: utf-8 -*-

import logging

from openerp import api, fields, models, _

_logger = logging.getLogger(__name__)

original_load = models.Model.load

@api.model
def load(self, fields, data):
    load_result = original_load(self, fields, data)
    context = self.env.context or {}
    if context.get("import_ignore_error"):
        record = set()
        for message in load_result.get("messages", []):
            if message['type'] == 'error':
                record.add(message['record'])
        if record:
            data_ignore = []
            for index, item in enumerate(data):
                if index not in record:
                    data_ignore.append(item)
            load_result = original_load(self, fields, data_ignore)
    return load_result

models.Model.load = load
