# Copyright 2018 Roel Adriaans <roel@road-support.nl>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': 'Send Multiple Invoices By Email',
    'version': '11.0.1.0.0',
    'summary': 'Mass send multiple invoices by email',
    'category': 'Tools',
    'license': 'AGPL-3',
    'author': 'Road-Support',
    'website': 'https://www.road-support.nl',
    'description': """With this module you can send invoices directly via email.
There is no need to select every email by hand anymore.""",
    'depends': [
        'account',
        'mail',
    ],
    'data': [
        'views/account_invoice.xml',
        'wizard/account_invoice_mail.xml',
    ],
    'images': ['static/description/wizard_01.png'],
    'demo': [],
    'test': [],
    'installable': True,
    'auto_install': False,
}
