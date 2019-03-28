/*
* @Author: D.Jane
* @Email: jane.odoo.sp@gmail.com
*/
odoo.define('pos_stock_quantity.popups', function (require) {
    "use strict";
    var gui = require('point_of_sale.gui');
    var PopupWidget = require('point_of_sale.popups');

    var Reminder = PopupWidget.extend({
        template: 'Reminder',

        click_cancel: function () {
            this.options.line.set_quantity('remove');
            this.gui.close_popup();
        },

        click_confirm: function () {
            this.options.line.set_quantity(this.options.max_available);
            this.gui.close_popup();
        }
    });

    gui.define_popup({name: 'order_reminder', widget: Reminder});
});
