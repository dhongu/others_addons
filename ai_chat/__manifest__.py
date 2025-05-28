# Copyright (C) 2024 - Michel Perrocheau (https://github.com/myrrkel).
# License LGPL-3.0 or later (https://www.gnu.org/licenses/algpl.html).
{
    'name': 'AI Chat',
    'version': '17.0.0.0.1',
    'author': 'Michel Perrocheau',
    'website': 'https://github.com/myrrkel',
    'summary': "Add a AI Bot user to chat with",
    'sequence': 0,
    'certificate': '',
    'license': 'LGPL-3',
    'depends': [
        'ai_connector',
        'mail',
        'bus',
    ],
    'category': 'AI',
    'complexity': 'easy',
    'qweb': [
    ],
    'demo': [
    ],
    'images': [
    ],
    'data': [
        'security/ir.model.access.csv',
        'security/security.xml',
        'data/ai_chat_data.xml',
        'data/ai_completion_data.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'ai_chat/static/src/js/channel_commands.js',
        ],
    },
    'auto_install': False,
    'installable': True,
    'application': False,
}
