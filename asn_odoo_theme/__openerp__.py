{
    'name': 'Odoo 9 Backend-Theme',
    'version': '1.0',
    'author': 'Ajeng Shilvie N',
    'description': '''
        For Community Series, change Default Black Odoo Backend Theme like Odoo 9 Enterprise
    ''',
    'category': 'Themes/ASN',
    'depends': [
        'base',
    ],
    'data': [
        'views/custom_view.xml',
    ],
    'images':[
            'static/description/main_screenshot.jpg',
    ],
    'css': ['static/src/css/styles.css'],
    'auto_install': False,
    'installable': True,
}
