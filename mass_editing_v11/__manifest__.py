# -*- coding: utf-8 -*-
# © 2016 Serpent Consulting Services Pvt. Ltd. (support@serpentcs.com)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    'name': 'mass_editing',
    'version': '11.0.1.1.0',
    'author': 'Serpent Consulting Services Pvt. Ltd., '
              'Tecnativa, '
              'Odoo Community Association (OCA)',
    'contributors': [
        'Oihane Crucelaegui <oihanecrucelaegi@gmail.com>',
        'Serpent Consulting Services Pvt. Ltd. <support@serpentcs.com>',
        'Jay Vora <jay.vora@serpentcs.com>'
    ],
    'category': 'Tools',
    'website': 'http://www.serpentcs.com',
    'license': 'GPL-3 or any later version',
    'summary': 'Mass Editing (adaptation  v 10.0 to 11.0)',# boris.gra
    # 'uninstall_hook': 'uninstall_hook',# boris.gra
    'depends': ['base'],
    'data': [
        'security/ir.model.access.csv',
        'views/mass_editing_view.xml',
        'views/basic_js.xml',# boris.gra
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
