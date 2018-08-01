(function (){
    'use strict';
     var website = openerp.website;
     var _t = openerp._t;
     website.add_template_file('/website_snippet_product/static/xml/s_product_carousel_modal.xml');
     website.openerp_website = {};
     website.snippet.options.s_product_carousel = website.snippet.Option.extend({

        s_product_carousel: function (type, value, $li) {

            if (type !== 'click') return;
            var self = this;
            self.$modal = $(openerp.qweb.render("website_snippet_product.s_product_carousel_modal",{}));
            self.$modal.appendTo('body');
            self.$modal.modal();

            self.$modal.on('shown.bs.modal', function () {
                self.$modal.find("#pin_mode").val(self.$target.attr('data-pin-mode'));
                self.$modal.find("#pin_nbr_element").val(self.$target.attr('data-pin-nbr-element'));
                self.$modal.find("#pin_nbr_product").val(self.$target.attr('data-pin-nbr-product'));
            });

            self.$modal.find("#sub_carousel").on('click', function () {
                var oldid=self.$target.attr('data-id-carousel');
                if (oldid==0){
                    var idc=Math.floor(Math.random() * 10001);
                    self.$target.attr('data-id-carousel', idc);
                }
                self.$target.attr('data-pin-mode', (self.$modal.find("#pin_mode").val()));
                self.$target.attr('data-pin-nbr-element', (self.$modal.find("#pin_nbr_element").val()));
                self.$target.attr('data-pin-nbr-product', (self.$modal.find("#pin_nbr_product").val()));
                self.$modal.modal('hide');
               // self.$target.data('snippet-view').redraw();
            });
        },


        drop_and_build_snippet: function () {
            this.s_product_carousel('click', null, null);
        },

        clean_for_save: function () {
            this.$target.find(".product_list_carrousel").empty();
        },

        //start: function () {
          //this.$target.data('snippet-view').redraw();
       // }
    });

})();