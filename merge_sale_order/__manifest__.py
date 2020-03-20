# -*- coding: utf-8 -*-

{
    'name': 'Merge Sale Order',
    'category': 'Sales',
    'summary': 'This module will merge sale order.',
    'version': '12.0.1.0.0',
    'website': 'http://www.aktivsoftware.com',
    'author': 'Aktiv Software',
    'description': 'Merge Sale Order',
    'license': "AGPL-3",

    'depends': [
        'sale_management'
    ],

    'data': [
        'wizard/merge_sale_order_wizard_view.xml',
    ],

    'images': [
        'static/description/banner.jpg',
    ],

    'installable': True,

}
