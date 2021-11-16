odoo.define('website_order_note_av.order_note',function (require) {
'use strict';
	require('web.dom_ready');
	var ajax = require('web.ajax');

    // Add the note in order
	$("button#o_payment_form_pay").bind("click", function (ev) {
		var website_order_note = $('#website_order_note').val();
		if($('#website_order_note').length > 0 && website_order_note){
		    ajax.jsonRpc('/order-note', 'call', {
	            'website_order_note': website_order_note
	        })
		}
	});
});