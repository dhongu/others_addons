# -*- coding: utf-8 -*-
# © 2016-2018 Akretion (Alexis de Lattre <alexis.delattre@akretion.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models,_
from odoo.exceptions import UserError
from odoo.tools import html2plaintext


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    report_type = fields.Selection(selection_add=[
        ('qweb-txt', 'Text'),
        ('qweb-txt-csv', 'CSV'),
        ('qweb-txt-zpl', 'zpl'),
        ('qweb-txt-prn', 'prn'),
        ('qweb-txt-inp', 'inp'),
        ])

    @api.model
    def render_report(self, res_ids,  data):
        if ( data.get('report_type') and   data.get('report_type').startswith('qweb-txt')):
            ext = data['report_type'].split('-')[-1]
            # That way, you can easily add qweb-txt-zpl' or others
            # without inheriting this method (you just need to do the
            # selection_add on the field 'report_type')
            report, exthtml =  self.render_qweb_html(res_ids, data=data)
            return report, ext
        else:
            return super(IrActionsReport, self).render_report( res_ids,  data)

    @api.model
    def _get_report_from_name(self, report_name):
        res = super(IrActionsReport, self)._get_report_from_name(report_name)
        if res:
            return res
        report_obj = self.env['ir.actions.report']
        qwebtypes = ['qweb-txt','qweb-txt-csv','qweb-txt-zpl','qweb-txt-prn','qweb-txt-inp']
        conditions = [('report_type', 'in', qwebtypes),
                      ('report_name', '=', report_name)]
        context = self.env['res.users'].context_get()
        return report_obj.with_context(context).search(conditions, limit=1)

    @api.model
    def render_txt(self, docids, data):
        report, exthtml = self.render_qweb_html(docids, data=data)
        report = html2plaintext(report)
        return report, 'txt'

    @api.model
    def render_txt_csv(self, docids, data):
        report, exthtml = self.render_qweb_html(docids, data=data)
        report = html2plaintext(report)
        return report, 'csv'

    @api.model
    def render_txt_zpl(self, docids, data):
        report, exthtml = self.render_qweb_html(docids, data=data)
        report = html2plaintext(report)
        return report, 'zpl'

    @api.model
    def render_txt_prn(self, docids, data):
        report, exthtml = self.render_qweb_html(docids, data=data)
        report = html2plaintext(report)
        return report, 'prn'

    @api.model
    def render_txt_inp(self, docids, data):
        report, exthtml = self.render_qweb_html(docids, data=data)
        report = html2plaintext(report)
        return report, 'inp'