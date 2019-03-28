# -*- coding: utf-8 -*-
{
    'name': 'POS Stock',
    'version': '1.0.0',
    'category': 'Point Of Sale',
    'author': 'D.Jane',
    'sequence': 10,
    'summary': 'Display Stocks on POS Location. Update Real-Time Quantity Available.',
    'description': "",
    'depends': ['point_of_sale'],
    'data': [
        'views/header.xml',
        'views/config.xml'
    ],
    'images': ['static/description/banner.png'],
    'qweb': ['static/src/xml/pos_stock.xml'],
    'installable': True,
    'application': True,
    'license': 'OPL-1',
    'currency': 'EUR',
}
