###################################################################################
#
#    Copyright (C) 2018 MuK IT GmbH
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
###################################################################################
{
    "name": "MuK Backend Theme", 
    "summary": "Odoo Community Backend Theme",
    "version": "12.0.1.5.2",
    "category": "Themes/Backend",
    "license": "AGPL-3",
    "author": "MuK IT",
    "website": "http://www.mukit.at",
    'live_test_url': 'https://mukit.at/r/SgN',
    "contributors": [
        "Mathias Markl <mathias.markl@mukit.at>",
    ],
    "depends": [
        "muk_web_utils",
    ],
    "excludes": [
        "web_enterprise",
    ],
    "data": [
        "template/assets.xml",
        "template/web.xml",
        "views/res_users.xml",
        "views/res_config_settings_view.xml",
        "data/res_company.xml",
    ],
    "qweb": [
        "static/src/xml/*.xml",
    ],
    "images": [
        'static/description/banner.png',
        'static/description/theme_screenshot.png'
    ],
    "external_dependencies": {
        "python": [],
        "bin": [],
    },
    "application": False,
    "installable": True,
    "auto_install": False,
    "uninstall_hook": "_uninstall_reset_changes",
}