// © 2017 Creu Blanca
// License AGPL-3.0 or later (https://www.gnuorg/licenses/agpl.html).
odoo.define('report_qweb_txt.report', function(require){
'use strict';

var ActionManager= require('web.ActionManager');
var crash_manager = require('web.crash_manager');
var framework = require('web.framework');

var make_report_url = function (action) {
    var report_urls = {
        'qweb-txt':     '/report/txt/' + action.report_name,
        'qweb-txt-csv': '/report/csv/' + action.report_name,
        'qweb-txt-zpl': '/report/zpl/' + action.report_name,
        'qweb-txt-prn': '/report/prn/' + action.report_name,
        'qweb-txt-inp': '/report/inp/' + action.report_name,
    };
    // We may have to build a query string with `action.data`. It's the place
    // were report's using a wizard to customize the output traditionally put
    // their options.
    if (_.isUndefined(action.data) || _.isNull(action.data) || (_.isObject(action.data) && _.isEmpty(action.data))) {
        if (action.context.active_ids) {
            var active_ids_path = '/' + action.context.active_ids.join(',');
            // Update the report's type - report's url mapping.
            report_urls = _.mapObject(report_urls, function (value, key) {
                return value += active_ids_path;
            });
        }
    } else {
        var serialized_options_path = '?options=' + encodeURIComponent(JSON.stringify(action.data));
        serialized_options_path += '&context=' + encodeURIComponent(JSON.stringify(action.context));
        // Update the report's type - report's url mapping.
        report_urls = _.mapObject(report_urls, function (value, key) {
            return value += serialized_options_path;
        });
    }
    return report_urls;
};



ActionManager.include({
    ir_actions_report: function (action, options){
        var self = this;
        var cloned_action = _.clone(action);

        if (cloned_action.report_type.startsWith('qweb-txt')) {
            framework.blockUI();
            var report_urls = make_report_url(action);
            var myWindow = window.open(report_urls[cloned_action.report_type], '_blank');
            if(cloned_action && options && !cloned_action.dialog){
                options.on_close();
            }
            this.dialog_stop();
            framework.unblockUI();

            return;
        }
        return self._super(action, options);
    }
});
});
