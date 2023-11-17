# Copyright 2020 NextERP Romania SRL
# License OPL-1.0 or later
# (https://www.odoo.com/documentation/user/14.0/legal/licenses/licenses.html#).

import logging

from odoo import api, models

_logger = logging.getLogger(__name__)


class Base(models.AbstractModel):
    _inherit = "base"

    @api.model
    def load_views(self, views, options=None):
        res = super().load_views(views, options)
        if res.get("fields_views"):
            for key in res.get("fields_views").keys():
                if res.get("fields_views").get(key):
                    view_values = res.get("fields_views").get(key)
                    if view_values.get("view_id"):
                        view = (
                            self.env["ir.ui.view"].sudo().browse(view_values["view_id"])
                        )
                        view_values["arch"] = view.get_paid_module_warning(
                            view_values["arch"]
                        )
        return res
