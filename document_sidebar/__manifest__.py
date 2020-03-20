# -*- coding: utf-8 -*-
{
    'license': 'LGPL-3',
    'name': "Document Sidebar",
    'summary': "Document sidebar in form view",
    'description': """
Attachments list
========================================
* Show attachment on the top of the forms
""",
    'author': "renjie <i@renjie.me>",
    'website': "https://renjie.me",
    'support': 'i@renjie.me',
    'category': 'Extra Tools',
    'version': '2.1',
    'depends': ['web'],
    'data': [
        'views/webclient_templates.xml',
    ],
    'images': [
        'static/description/main_screenshot.png',
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
}