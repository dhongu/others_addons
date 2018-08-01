##############################################################################
#
#    Sajad KK <kksajad@gmail.com>
#    Copyright (C) 2015
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
{
    'name': 'Monetary widget for list view',
    'version': '1.5',
    'sequence': 150,
    'category': 'Web',
    'summary': 'Monetary widget for list view',
    'description': """
=======================

This module implements a monetary widget for tree view. The module expect a currency field 'currency_id' or specified
as options="{'currency_field': 'custom_currency_id'}".

    eg. usage: <field name="amount_total" widget="monetary" />

""",
    'author': 'Sajad KK',
    'depends': ['web'],
    'data': ['views/templates.xml'],
    'installable': True,
    'application': False,
    'auto_install': False,
}
