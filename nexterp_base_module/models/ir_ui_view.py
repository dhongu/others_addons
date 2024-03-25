# Copyright 2020 NextERP Romania SRL
# License OPL-1.0 or later
# (https://www.odoo.com/documentation/user/14.0/legal/licenses/licenses.html#).

import json
import logging

from lxml import etree

from odoo import _, api, models

_logger = logging.getLogger(__name__)


class IrUIView(models.Model):
    _inherit = "ir.ui.view"

    @api.model
    def has_paid_module_installed(self, view=False):
        if view:
            external_id = view.get_external_id().get(view.id)
            if external_id:
                (module_name, _name) = external_id.split(".")
                company = self.env.company.id
                module = self.env["ir.module.module.paid"].search(
                    [("company_id", "=", company), ("module_name", "=", module_name)]
                )
                if module and module.paid_state in ("not_paid", "blocked"):
                    return module.paid_state
        return False

    def get_paid_module_warning(self, arch=False):
        self.ensure_one()
        if not arch:
            arch = self.arch
        IrParamSudo = self.env["ir.config_parameter"].sudo()
        is_neutralized = IrParamSudo.get_param("database.is_neutralized", default=False)
        if is_neutralized:
            return arch
        pay_state = self.has_paid_module_installed(self)
        if pay_state and self.type in ("tree", "form", "kanban"):

            notif_message = _(
                "Your using a module that you didn't buy or subscribed.\n"
                "Please contact the author."
            )
            eview = etree.fromstring(arch)
            external_id = self.get_external_id()
            if external_id:
                [external_id] = external_id.values()
                (module_name, _name) = external_id.split(".")
                company = self.env.company.id
                paid_module = self.env["ir.module.module.paid"].search(
                    [
                        ("company_id", "=", company),
                        ("module_name", "=", module_name),
                    ]
                )
                if paid_module:
                    module = paid_module.module_id
                    notif_message = _(
                        "Your using module %s that you didn't buy or subscribed.\n"
                        "Please contact the author %s."
                    ) % (module.name, module.author)
            notif = etree.Element(
                "div",
                {
                    "class": "alert alert-danger",
                    "name": "paid_module_notification",
                    "role": "alert",
                    "style": "height: 40px; margin-bottom:0px;",
                    "text": notif_message,
                },
            )

            if self.type == "tree":
                elem = eview.xpath("/tree/header")
                if len(eview) and len(elem):
                    elem = elem[0]
                    elem.insert(0, notif)
                else:
                    elem = eview.xpath("tree")
                    if len(eview) and len(elem):
                        elem = elem[0]
                        elem.insert(0, notif)
            elif self.type == "form":
                elem = eview.xpath("header")
                if not elem:
                    elem = eview.xpath("/form")
                    if len(eview) and len(elem):
                        elem = elem[0]
                        elem.insert(0, notif)
                elif len(eview) and len(elem):
                    elem = elem[0]
                    elem.addnext(notif)
            elif self.type == "kanban":
                elem = eview.xpath("templates")
                if len(eview) and len(elem):
                    elem = elem[0]
                    elem.insert(0, notif)
            if pay_state == "blocked":
                buttons = eview.xpath("//button")
                for node in buttons:
                    node.set("invisible", "1")
                    if node.get("modifiers"):
                        modifiers = json.loads(node.get("modifiers"))
                        modifiers["invisible"] = True
                        node.set("modifiers", json.dumps(modifiers))
            arch = etree.tostring(eview, encoding="unicode")
        return arch

    @api.depends("arch_db", "arch_fs", "arch_updated")
    @api.depends_context("read_arch_from_file", "lang")
    def _compute_arch(self):
        res = super()._compute_arch()
        for view in self:
            view.arch = view.get_paid_module_warning()
        return res

    def _apply_view_inheritance(self, source, inherit_tree):
        res = super()._apply_view_inheritance(source, inherit_tree)
        if "paid_module_notification" not in etree.tostring(res, encoding="unicode"):
            for view in inherit_tree[self]:
                if view.has_paid_module_installed():
                    res = self.get_paid_module_warning(res)
        return res
