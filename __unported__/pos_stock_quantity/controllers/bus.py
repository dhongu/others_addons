# -*- coding: utf-8 -*-

from odoo import SUPERUSER_ID
from odoo.http import request, route
from odoo.addons.bus.controllers.main import BusController


class BusControllerInherit(BusController):
    def _poll(self, dbname, channels, last, options):
        if request.session.uid:
            channels = list(channels)
            channels.append((request.db, 'pos.stock.channel'))
        return super(BusControllerInherit, self)._poll(dbname, channels, last, options)