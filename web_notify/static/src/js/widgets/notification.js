odoo.define('web_notify.Notification', function (require) {
    "use strict";

    var Notification = require('web.Notification');

    Notification.include({
        icon_mapping: {
            'success': 'fa-thumbs-up',
            'danger': 'fa-exclamation-triangle',
            'warning': 'fa-exclamation',
            'info': 'fa-info',
            'default': 'fa-lightbulb-o',
        },
        init: function () {
            this._super.apply(this, arguments);
            // Delete default classes
            this.className = this.className.replace(' o_error', '');
            // Add custom icon and custom class
            this.icon = (this.type in this.icon_mapping) ?
                this.icon_mapping[this.type] :
                this.icon_mapping['default'];
            this.className += ' o_' + this.type;

             this.play_sound(this.type);

        },


        play_sound: function(sound) {
            var src = '';
            if (sound === 'danger') {
                src = "/point_of_sale/static/src/sounds/error.wav";
            } else if (sound === 'warning') {
                src = "/web_notify/static/src/sounds/exclamation.wav";
            } else if (sound === 'success') {
                src = "/point_of_sale/static/src/sounds/bell.wav";
            } else {
                 src = "/web_notify/static/src/sounds/notify.wav";
            }
            $('body').append('<audio src="'+src+'" autoplay="true"></audio>');
        },


    });

});
