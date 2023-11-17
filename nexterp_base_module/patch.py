# Copyright 2020 NextERP Romania SRL
# License OPL-1.0 or later
# (https://www.odoo.com/documentation/user/14.0/legal/licenses/licenses.html#).

import ast
import logging

import odoo.tools as tools
from odoo import modules
from odoo.modules.module import get_module_path, module_manifest
from odoo.tools import pycompat

_logger = logging.getLogger(__name__)
_original_load_information_from_description_file = (
    modules.module.load_information_from_description_file
)


def _patch_load_information_from_description_file(module, mod_path=None):
    res = _original_load_information_from_description_file(module, mod_path=None)
    if res:
        if not mod_path:
            mod_path = get_module_path(module, downloaded=True)
        res["extra_buy"] = False
        manifest_file = module_manifest(mod_path)
        if manifest_file:
            f = tools.file_open(manifest_file, mode="rb")
            try:
                all_info = ast.literal_eval(pycompat.to_text(f.read()))
            finally:
                f.close()
            res["extra_buy"] = all_info.get("extra_buy", False)

    return res


def post_load():
    _logger.info("Applying patch module_change_extra_buy")
    modules.module.load_information_from_description_file = (
        _patch_load_information_from_description_file
    )
    modules.load_information_from_description_file = (
        _patch_load_information_from_description_file
    )
