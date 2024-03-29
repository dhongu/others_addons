# ©  2018 Terrabit
# See README.rst file on addons root folder for license details

{
    "name": "List View General Buttons",
    "summary": "General Buttons in List View ",
    "version": "15.0.1.0.0",
    "author": "Terrabit, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/web",
    "category": "Generic Modules",
    "depends": ["base", "web"],
    "license": "AGPL-3",
    # "data": ["views/assets.xml"],
    "assets": {
        "web.assets_backend": [
              "web_list_view_general_buttons/static/src/js/list_controller.js",
        ]
    },
    "qweb": ["static/src/xml/*.xml"],
    "development_status": "Beta",
    "maintainers": ["dhongu"],
}
