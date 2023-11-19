# Copyright 2021 NextERP Romania SRL
# License OPL-1.0 or later
# (https://www.odoo.com/documentation/user/15.0/legal/licenses/licenses.html#).


import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class DatabaseController(http.Controller):
    @http.route(
        "/mods_state_update",
        methods=["GET", "POST"],
        type="json",
        auth="none",
        csrf=False,
    )
    def DatabaseLog(self, **post):
        values = request.jsonrequest
        res = {"message": "ok"}
        try:
            res = (
                request.env["publisher_warranty.contract"]
                .sudo()
                .populate_paid_modules(values)
            )
        except Exception as e:
            _logger.info("Error log database stat %s." % e)
        return res
