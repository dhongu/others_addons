# Copyright 2020 NextERP Romania SRL
# License OPL-1.0 or later
# (https://www.odoo.com/documentation/user/14.0/legal/licenses/licenses.html#).

import json
import logging
from datetime import timedelta

import urllib3

from odoo import api, fields
from odoo.models import AbstractModel

_logger = logging.getLogger(__name__)


class PublisherWarrantyContract(AbstractModel):
    _inherit = "publisher_warranty.contract"

    @api.model
    def populate_paid_modules(self, paid_modules):
        for company, modules in paid_modules.items():

            company = int(company) or self.env.company.id
            for module_name, val in modules.items():
                module = (
                    self.env["ir.module.module"]
                    .sudo()
                    .search([("name", "=", module_name)], limit=1)
                )
                if module:
                    paid_module = (
                        self.env["ir.module.module.paid"]
                        .sudo()
                        .search(
                            [
                                ("company_id", "=", company),
                                ("module_id", "=", module.id),
                            ]
                        )
                    )
                    if paid_module:
                        paid_module.paid_state = val
                    else:
                        if module:
                            self.env["ir.module.module.paid"].sudo().create(
                                {
                                    "company_id": company,
                                    "module_id": module.id,
                                    "paid_state": val,
                                }
                            )

    @api.model
    def _get_publisher_logs(self, cron_mode=True):
        IrParamSudo = self.env["ir.config_parameter"].sudo()
        buy_mods_send = IrParamSudo.get_param("buy_mods_send")
        start_date = fields.Date.from_string(fields.Datetime.now()) - timedelta(days=7)
        send_data = self.env.context.get("send_data")
        if cron_mode and (
            not buy_mods_send or fields.Date.from_string(buy_mods_send) <= start_date
        ):
            send_data = True
        if send_data:
            try:
                buy_mods = (
                    self.env["ir.module.module"]
                    .sudo()
                    .search([("extra_buy", "=", True)])
                )
                authors = set(buy_mods.mapped("website"))
                for author in authors:
                    auth_buy_mods = buy_mods.filtered(lambda m: m.website == author)
                    try:
                        modules = self.get_buy_mod_logs(auth_buy_mods)
                        if modules:
                            self.populate_paid_modules(modules.get("modules"))
                    except Exception:
                        if cron_mode:  # we don't want to see any stack trace in cron
                            return False
            except Exception:
                if cron_mode:
                    return False  # we don't want to see any stack trace in cron
                else:
                    raise
            return True
        return True

    @api.model
    def get_buy_mod_logs(self, auth_buy_mods):
        """
        Utility method to send a publisher warranty get logs messages.
        """
        send_data = self._get_message()
        companies = (
            self.env["res.company"]
            .sudo()
            .search_read([], ["name", "vat", "email", "phone"])
        )
        installed_mods = auth_buy_mods.filtered(
            lambda m: m.state in ["installed", "to upgrade", "to remove"]
        )
        send_data["installed_modules"] = installed_mods.read(
            ["name", "latest_version", "author", "state"]
        )
        send_data["author_modules"] = auth_buy_mods.read(
            ["name", "latest_version", "author", "state"]
        )
        send_data["companies"] = companies
        url = auth_buy_mods[0].website + "/mods_update"
        json1 = json.dumps(send_data)
        http_post = urllib3.PoolManager()
        resp = http_post.request(
            "POST", url, body=json1, headers={"Content-Type": "application/json"}
        )
        response = json.loads(resp.data)
        return response.get("result")

    def update_notification(self, cron_mode=True):
        """
        Utility method to send a publisher warranty get logs messages.
        """
        res = super().update_notification(cron_mode=cron_mode)
        self._get_publisher_logs(cron_mode=True)
        return res
