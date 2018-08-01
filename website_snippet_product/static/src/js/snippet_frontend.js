(function () {
    'use strict';
   var website = openerp.website,
          qweb = openerp.qweb;
        qweb.add_template('/website_snippet_product/static/xml/product.xml');
        website.snippet.animationRegistry.s_product_carousel = website.snippet.Animation.extend({

        selector: "section.s_product_carousel",

        start : function() {
            var self = this;
               self.redraw();
            return this._super();
        },

        redraw: function(){
            var self = this;
            var max_item =parseInt(self.$target.attr('data-pin-nbr-element'));
            var mode =self.$target.attr('data-pin-mode');
            var idc =parseInt(self.$target.attr('data-id-carousel'));
            if (idc>0){
                self.$target.find("div[id='carousel-product']").attr("id",'carousel-product'+idc);
                self.$target.find("a[href='#carousel-product']").each(function() {
                    $(this).attr("href",'#carousel-product'+idc);
                });
            }
            var html = document.documentElement;
            var lang=html.getAttribute('lang').replace('-', '_');
                openerp.jsonRpc('/get_product_list','call', {"mode":mode,"max_item":max_item,"lang":lang}).then(function(data) {
                           self.render_top(data);
                });
        },


        render_top: function(obj){
            var self = this;
            var nbr_item =parseInt(self.$target.attr('data-pin-nbr-product')); // nbr product in table
            var lenobj=obj.length;
            var nbr_carrousel=Math.ceil((lenobj/nbr_item));
            var product_carrousel = this.$target.find(".product_list_carrousel");
            $(product_carrousel).empty();
            for (var carrousel = 1; carrousel <= nbr_carrousel; carrousel++) {
           var carrousel_item = [];

                var carrousel_active="item"
                if (carrousel==1){
                    carrousel_active="item active"
                }
                var carrousel_table="product_carrousel_table_"+carrousel

                //ajout le caroussel
                carrousel_item.push(qweb.render("website.snippet.product_carrousel",
                {'carrousel_nbr_prod':nbr_item,
                'carrousel_table':carrousel_table,
                'carrousel_active': carrousel_active,
                "carrousel_id":carrousel}));

                $(carrousel_item).appendTo(product_carrousel);

                var product_table = this.$target.find("."+carrousel_table);
                var prods = [];
                var cmpt=0;

                $.each(obj, function (e, objet) {

                    if ((cmpt>=((carrousel-1)*(nbr_item)))&&(cmpt<=(((carrousel)*(nbr_item)))-1)) {
                            prods.push(objet);
                    }
                    cmpt=cmpt+1;
                });
                $(product_table).empty();
                $(prods).appendTo(product_table);

            };
        },

});

})();



$(document).ready(function () {
function timeclick(){
    $('.s_product_carousel').each(function () {
          var oe_website_sale = this;
          $('.a-submit', oe_website_sale).off('click').on('click', function () {
          $(this).closest('form').submit();
    });
});
};
setTimeout (timeclick, 2000);
});
