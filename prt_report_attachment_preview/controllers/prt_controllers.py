from odoo import http
from odoo.http import request
from odoo.tools.safe_eval import safe_eval
from odoo.addons.web.controllers.main import ReportController

import werkzeug
import json
import time
from odoo.http import content_disposition, route, request

# List of content types that will be opened in browser
OPEN_BROWSER_TYPES = ['application/pdf']


######################
# Report Controllers #
######################

class PrtReportController( ReportController):

    @route()
    def report_routes(self, reportname, docids=None, converter=None, **data):

        if converter == 'pdf':
            report = request.env['ir.actions.report']._get_report_from_name(reportname)
            context = dict(request.env.context)
            if docids:
                docids = [int(i) for i in docids.split(',')]
            if data.get('options'):
                data.update(json.loads(data.pop('options')))
            if data.get('context'):
                # Ignore 'lang' here, because the context in data is the one from the webclient *but* if
                # the user explicitely wants to change the lang, this mechanism overwrites it.
                data['context'] = json.loads(data['context'])
                if data['context'].get('lang'):
                    del data['context']['lang']
                context.update(data['context'])

            pdf = report.with_context(context).render_qweb_pdf(docids, data=data)[0]

            # Get filename for report
            filepart = "report"
            if docids:
                if len(docids) > 1:
                    filepart = "%s (x%s)" % (request.env['ir.model'].sudo().search([('model', '=', report.model)]).name, str(len(docids)))
                elif len(docids) == 1:
                    obj = request.env[report.model].browse(docids)
                    if report.print_report_name:
                        filepart = safe_eval(report.print_report_name, {'object': obj, 'time': time})



            pdfhttpheaders = [('Content-Type', 'application/pdf'), ('Content-Length', len(pdf)),
                              ('Content-Disposition', 'filename="%s.pdf"' % (filepart))]
            return request.make_response(pdf, headers=pdfhttpheaders)




        return super(PrtReportController, self).report_routes(reportname, docids, converter, **data)
