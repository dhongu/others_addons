odoo.define('mass_editing.include', function (require) {
"use strict";
var BasicModel = require('web.BasicModel');

BasicModel.include({
    _parseServerData: function (fieldNames, element, data) {
        var self = this;
        _.each(fieldNames, function (fieldName) {
            var field = element.fields[fieldName];
            var val = data[fieldName];
            if (field.type === 'many2one') {
                // process many2one: split [id, nameget] and create corresponding record
                if (val !== false && val !== null) { //# boris.gra
//# boris.gra                if (val !== false) {
                    // the many2one value is of the form [id, display_name]
                    var r = self._makeDataPoint({
                        modelName: field.relation,
                        fields: {
                            display_name: {type: 'char'},
                            id: {type: 'integer'},
                        },
                        data: {
                            display_name: val[1],
                            id: val[0],
                        },
                        parentID: element.id,
                    });
                    data[fieldName] = r.id;
                } else {
                    // no value for the many2one
                    data[fieldName] = false;
                }
            } else {
                data[fieldName] = self._parseServerValue(field, val);
            }
        });
    }

});

});
