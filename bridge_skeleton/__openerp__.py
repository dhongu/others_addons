# -*- coding: utf-8 -*-
#################################################################################
#
#   Copyright (c) 2015-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
#   See LICENSE file for full copyright and licensing details.
#
#################################################################################

{
    'name': 'Odoo: Bridge Skeleton',
    'version': '1.0',
    'author': 'Webkul Software Pvt. Ltd.',
    'summary': 'Core of Webkul Bridge Modules',
    'description': """
        This is core for all basic operations features provided in Webkul's Bridge Modules.
    """,
    'website': 'http://www.webkul.com',
    'images': [],
    'depends': ['sale','stock','account_accountant','account','account_cancel','delivery'],
    'category': 'Bridge Module',
    'data': ['views/inherited_view.xml'],
    'installable': True,
    'auto_install': False,
}
