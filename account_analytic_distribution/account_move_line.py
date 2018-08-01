# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import models, api, _
from openerp.exceptions import Warning
import logging
_logger = logging.getLogger(__name__)


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    @api.one
    @api.constrains('analytic_account_id')
    def check_account_type(self):
        if self.analytic_account_id.type == 'distribution':
            raise Warning(_(
                'You can not choose an analytic account of type "Distribution"'
                ' on a journal entry, you need to split lines manually'))
