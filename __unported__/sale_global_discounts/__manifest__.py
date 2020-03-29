# -*- coding: utf-8 -*-
#╔══════════════════════════════════════════════════════════════════╗
#║                                                                  ║
#║                ╔═══╦╗       ╔╗  ╔╗     ╔═══╦═══╗                 ║
#║                ║╔═╗║║       ║║ ╔╝╚╗    ║╔═╗║╔═╗║                 ║
#║                ║║ ║║║╔╗╔╦╦══╣╚═╬╗╔╬╗ ╔╗║║ ╚╣╚══╗                 ║
#║                ║╚═╝║║║╚╝╠╣╔╗║╔╗║║║║║ ║║║║ ╔╬══╗║                 ║
#║                ║╔═╗║╚╣║║║║╚╝║║║║║╚╣╚═╝║║╚═╝║╚═╝║                 ║
#║                ╚╝ ╚╩═╩╩╩╩╩═╗╠╝╚╝╚═╩═╗╔╝╚═══╩═══╝                 ║
#║                          ╔═╝║     ╔═╝║                           ║
#║                          ╚══╝     ╚══╝                           ║
#║ SOFTWARE DEVELOPED AND SUPPORTED BY ALMIGHTY CONSULTING SERVICES ║
#║                   COPYRIGHT (C) 2016 - TODAY                     ║
#║                   http://www.almightycs.com                      ║
#║                                                                  ║
#╚══════════════════════════════════════════════════════════════════╝
{
    'name': 'Sale Global Discounts',
    'category': 'Sales',
    'version': '1.0',
    'author' : 'Almighty Consulting Services',
    'support': 'info@almightycs.com',
    'website' : 'http://www.almightycs.com',
    'summary': """Apply Global Discounts on Sale Orders based on fixed amounts and percentage""",
    'description': """Apply Global Discounts on Sale Orders based on fixed amounts and percentage
    Global Discounts
    Global Discount
    Fixed Amount Discount
    Discount on Total
    Discount in Sale
    Global Discount in Sale""",
    'depends': ['sale','account'],
    'data': [
        'views/sale_view.xml',
        'views/res_config_view.xml',
    ],
    'images': [
        'static/description/discount_cover_almightycs_turkesh.png',
    ],
    'installable': True,
    'auto_install': False,
    'price': 14,
    'currency': 'EUR',
}


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
