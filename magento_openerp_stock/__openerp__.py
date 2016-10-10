# -*- coding: utf-8 -*-
#################################################################################
#
#    Copyright (c) 2015-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
#
#################################################################################

{
    'name': 'MOB Stock Management',
    'version': '2.4',
    'category': 'Generic Modules',
    'sequence': 1,
    'summary': 'MOB Stock Extension',
    'description': """	
MOB Stock Extesnion
=========================
    Stock Management From Odoo To Magento.

    This module will automatically manage stock from odoo to magento during below operations.

    1. Sales Order
    2. Purchase Order
    3. Point Of Sales
	
	NOTE : This module works very well with latest version of magento 1.9 and latest version of Odoo 8.0.
    """,
    'author': 'Webkul Software Pvt Ltd.',
    'depends': ['magento_bridge'],
    'website': 'http://www.webkul.com',
    'data': [
            'views/res_config_view.xml',
            ],
    'application': True,
    'installable': True,
    'active': False,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
