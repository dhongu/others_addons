odoo.define('web_export_view', function (require) {
"use strict";

		var core = require('web.core');
		var Sidebar = require('web.Sidebar');
		var ViewManager = require('web.ViewManager');
		var ListController = require('web.ListController');
		var session = require('web.session');


		var QWeb = core.qweb;

		var _t = core._t;

		ListController.include({

			 renderButtons: function($node) {

			 this._super.apply(this, arguments);

					 if (this.$buttons) {
							 let filter_button = this.$buttons.find('.export_treeview_xls');
               //  on click on the button with class export_treeview_xls call the function export_list_view
							 filter_button && filter_button.click(this.proxy('export_list_view')) ;
					 }
			 },
			 export_list_view: function () {

					 var self = this,
							 view = this.getParent(),
							 children = view.getChildren();

					 var export_columns_keys = [];
					 var export_columns_names = [];
					 var columns_tab = [];
					 var rows_tab = [];
           // find the first tr of table for the columns labels
					 view.$el.find('th.o_list_record_selector ').closest('tr').each(function (i, el) {
							 var ihtml = el.innerHTML + ''; // get html content of the tr
							 var extractedTdArray = ihtml.split("</th>") // split tr in array of th

               // get the text content of each th
							 extractedTdArray.forEach(function(elt){
								 var val = elt.substring(elt.indexOf(">") + 1)
								 if(val){
									 columns_tab.push(val)
								 }
							 });

					 });

					 var export_rows = [];
           // find the all ckecked rows
					 view.$el.find('td.o_list_record_selector input:checked').closest('tr').each(function (i, el) {
							 rows_tab = []
							 var ihtml = el.innerHTML + '';
							 var extractedData = ihtml.split("</td>")
							 extractedData.forEach(function(elt){
								 var val = elt.substring(elt.indexOf(">") + 1) // get the td content
								 if(val != undefined){
									 if(val.indexOf(">") < 0 ){ // if the content of the td is not html content
										 rows_tab.push(val)
									 }
								 }
							 });
							 export_rows.push(rows_tab)
					 });
           //  if there is no checked row export all rows in the view
					 if(export_rows.length == 0){
						 view.$el.find('td.o_list_record_selector').closest('tr').each(function (i, el) {
								 rows_tab = []
								 var ihtml = el.innerHTML + '';
								 var extractedData = ihtml.split("</td>")
								 extractedData.forEach(function(elt){
									 var val = elt.substring(elt.indexOf(">") + 1)
									 if(val != undefined){
										 if(val.indexOf(">") <0 ){
											 rows_tab.push(val)
										 }
									 }
								 });
								 export_rows.push(rows_tab)
						 });
					 }
					 columns_tab.shift()
					 export_columns_names = columns_tab

					 $.blockUI();
					 this.getSession().get_file({
							 url: '/web/export/xls_view',
							 data: {data: JSON.stringify({
									 model: view.env.modelName,
									 headers: export_columns_names,
									 rows: export_rows
							 })},
							 complete: $.unblockUI
					 });

			 }

	 });

});
