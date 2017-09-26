odoo.define('import_ignore_error', function (require) {
"use strict";

var core = require('web.core');
var DataImport = require('base_import.import').DataImport;
DataImport.include({
    call_import: function(kwargs) {
        var self = this;
        self.parent_context = _.extend(
            self.parent_context || {},
            {import_ignore_error: self.$('#oe_import_ignore_error').prop('checked')}
        );
        return self._super.call(self, kwargs);
    }
});

});