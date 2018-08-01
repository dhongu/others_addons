# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) Monoyer Fabian (info@olabs.be)
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
    'name': "Snippet top product",
    'author': "O'Labs",
    'website': "http://www.olabs.be",
    'description': """

     Add a snippet dynamics, displays the products

     - Last sales
     - Top sales
     - Only in promo
     - Only new poducts
     - Latest updated

     Drag and drop the snippet to your page.

    """,
    'price': 20.00,
    'currency': 'EUR',
    'category': 'website',
    'version': '1.0',
    'depends': ['website','website_sale',"website_less"],
    'live_test_url': 'http://custo.olabs.be/web/login?db=demo0010&login=demo',
    'data': [
        'views/snippets.xml',
        'views/snippet_carousel.xml',
        ],
    'images':[
        'static/images/printscreen-0.png',
        'static/images/printscreen-modal-0.png',
        'static/images/printscreen-modal-1.png',
              ],
    'installable': True,
}
