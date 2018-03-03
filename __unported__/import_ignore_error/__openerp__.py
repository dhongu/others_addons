# -*- coding: utf-8 -*-
{
    'license': 'LGPL-3',
    'name': "Import Ignore Error",
    'summary': "Model import data ignore error",
    'description': """
    """,
    'author': "renjie <i@renjie.me>",
    'website': "https://renjie.me",
    'support': 'i@renjie.me',
    'category': 'Extra Tools',
    'version': '1.0',
    'depends': ['base_import'],
    'qweb': [
        "static/src/xml/import.xml",
    ],
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