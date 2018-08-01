openerp.listview_monetary = function(instance) {
    instance.web.list.columns.add('field.monetary','instance.web.list.FieldMonetary');

    instance.web.list.FieldMonetary = instance.web.list.Column.extend({
        /**
         * Return amount with currency symbol
         *
         * @private
         */
        init: function() {
            this._super.apply(this, arguments);

        },
        _format: function (row_data, options) {
            if (this.options && typeof this.options === 'string')  {
               // this.options = instance.web.py_eval(this.node.attrs.options || '{}');
                this.options = this.options.replace(/'/g,'"')
                this.options = JSON.parse(this.options);
            }
            var currency_field = (this.options && this.options.currency_field) || this.currency_field || 'currency_id';
            var currency_id = row_data[currency_field] && row_data[currency_field].value[0];
            var digits_precision = this.digits || (currency && currency.digits);
            var value = instance.web.format_value(row_data[this.id].value || 0, {type: this.type, digits: digits_precision}, options.value_if_empty);
            var currency = instance.session.get_currency(currency_id);
            if (currency) {
                if (currency.position === "after") {
                    value += '&nbsp;' + currency.symbol;
                } else {
                    value = currency.symbol + '&nbsp;' + value;
                }
            }
            return value;
        }
    });

    instance.web.Session.include( /** @lends instance.web.Session# */{
        init: function() {
            this._super.apply(this, arguments);
            this.currencies = {};
        },
        load_modules: function() {
            var self = this;
            return this.rpc('/web/session/modules', {}).then(function(result) {
                var all_modules = _.uniq(self.module_list.concat(result));
                var to_load = _.difference(result, self.module_list).join(',');
                self.module_list = all_modules;

                var loaded = $.when(self.load_currencies(), self.load_translations());
                var datejs_locale = "/web/static/lib/datejs/globalization/" + self.user_context.lang.replace("_", "-") + ".js";

                var file_list = [ datejs_locale ];
                if(to_load.length) {
                    loaded = $.when(
                        loaded,
                        self.rpc('/web/webclient/csslist', {mods: to_load}).done(self.load_css.bind(self)),
                        self.load_qweb(to_load),
                        self.rpc('/web/webclient/jslist', {mods: to_load}).done(function(files) {
                            file_list = file_list.concat(files);
                        })
                    );
                }
                return loaded.then(function () {
                    return self.load_js(file_list);
                }).done(function() {
                    self.on_modules_loaded();
                    self.trigger('module_loaded');
                    if (!Date.CultureInfo.pmDesignator) {
                        // If no am/pm designator is specified but the openerp
                        // datetime format uses %i, date.js won't be able to
                        // correctly format a date. See bug#938497.
                        Date.CultureInfo.amDesignator = 'AM';
                        Date.CultureInfo.pmDesignator = 'PM';
                    }
                });
            });
        },
        load_currencies: function() {
            this.currencies = {};
            var self = this;
            return new openerp.web.Model("res.currency").query(["symbol", "position", "decimal_places"]).all()
                    .then(function(value) {
                        _.each(value, function(k){
                            self.currencies[k.id] = {'symbol': k.symbol, 'position': k.position, 'digits': [69,k.decimal_places]};
                        });
                    });
        },
        get_currency: function(currency_id) {
            return this.currencies[currency_id];
        }
    });

};

