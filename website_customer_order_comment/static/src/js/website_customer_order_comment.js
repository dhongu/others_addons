odoo.define('website_customer_order_comment.payment', function(require) {
    "use strict";

    var ajax = require('web.ajax');

    $(document).ready(function() {
        'use strict';
        $('button[name="o_payment_submit_button"]').bind("click", function(ev) {
            var customer_comment = $('#customer_comment').val();
            ajax.jsonRpc('/shop/customer_comment/', 'call', {
                'comment': customer_comment
            })
        });
    });
});