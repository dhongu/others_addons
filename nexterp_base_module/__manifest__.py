# Copyright 2020 NextERP Romania SRL
# License OPL-1.0 or later
# (https://www.odoo.com/documentation/user/14.0/legal/licenses/licenses.html#).
{
    "name": "NextERP Base",
    "summary": "NextERP Base",
    "version": "15.0.0.0.11",
    "category": "Localisation",
    "author": "NextERP Romania",
    "website": "https://www.nexterp.ro",
    "support": "odoo_apps@nexterp.ro",
    "depends": ["mail"],
    "data": [
        "data/config_data.xml",
        "data/ir_cron_data.xml",
        "security/ir.model.access.csv",
    ],
    "installable": True,
    "auto_install": True,
    "development_status": "Mature",
    "maintainers": ["feketemihai"],
    "images": ["static/description/apps_icon.png"],
    "post_load": "post_load",
    "license": "OPL-1",
}
