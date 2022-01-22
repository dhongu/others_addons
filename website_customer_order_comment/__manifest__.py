# -*- coding: utf-8 -*-
# Part of AppJetty. See LICENSE file for full copyright and licensing details.

{
    "name": "Customer Order Comment",
    "author": "AppJetty",
    'license': 'OPL-1',
    "version": "15.0.1.0.0",
    "category": "Website",
    "website": "https://www.appjetty.com/",
    "description": "This module is used for add customer order comment section at payment page",
    "summary": "Know your customer's comments, view it on checkout page",
    "depends": ['website_sale'],
    "data": [
        'views/customer_comment_config_view.xml',
        'views/sale_order_view.xml',
        'views/template.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'website_customer_order_comment/static/src/js/website_customer_order_comment.js'
        ],
    },
    'images': ['static/description/customer-oder-comment-large.png'],
    'installable': True,
    'auto_install': False,
    'support': 'support@appjetty.com',
}
