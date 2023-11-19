# Copyright 2020 NextERP Romania SRL
# License OPL-1.0 or later
# (https://www.odoo.com/documentation/user/14.0/legal/licenses/licenses.html#).
import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)


class IrModule(models.Model):
    _inherit = "ir.module.module"

    extra_buy = fields.Boolean("Extra Buy Module", default=False)

    @staticmethod
    def get_updated_values_from_terp(self, terp):
        return {
            "description": terp.get("description", ""),
            "shortdesc": terp.get("name", ""),
            "author": terp.get("author", "Unknown"),
            "maintainer": terp.get("maintainer", False),
            "contributors": ", ".join(terp.get("contributors", [])) or False,
            "website": terp.get("website", ""),
            "license": terp.get("license", "LGPL-3"),
            "sequence": terp.get("sequence", 100),
            "application": terp.get("application", False),
            "auto_install": terp.get("auto_install", False) is not False,
            "icon": terp.get("icon", False),
            "summary": terp.get("summary", ""),
            "url": terp.get("url") or terp.get("live_test_url", ""),
            "to_buy": terp.get("to_buy", False),
            "extra_buy": terp.get("extra_buy", False),
        }

    def button_upgrade(self):
        res = super().button_upgrade()
        send_model = self.env["publisher_warranty.contract"].with_context(
            send_data=True
        )
        buy_mods = self.filtered(lambda m: m.extra_buy)
        if buy_mods:
            send_model._get_paid_modules_logs(cron_mode=False)
        return res

    def button_install(self):
        res = super().button_install()
        send_model = self.env["publisher_warranty.contract"].with_context(
            send_data=True
        )

        buy_mods = self.filtered(lambda m: m.extra_buy)
        if buy_mods:
            send_model._get_paid_modules_logs(cron_mode=False)
        return res

    def button_uninstall(self):
        res = super().button_uninstall()
        send_model = self.env["publisher_warranty.contract"].with_context(
            send_data=True
        )

        buy_mods = self.filtered(lambda m: m.extra_buy)
        if buy_mods:
            send_model._get_paid_modules_logs(cron_mode=False)
        return res


IrModule.get_values_from_terp = IrModule.get_updated_values_from_terp
