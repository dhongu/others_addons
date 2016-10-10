odoo.define('bus_enhacement', function (require) {
    var bus = require('bus.bus');

    openerp.web.WebClient.include({
        init: function(parent, client_options){
            this._super(parent, client_options);
            this.known_bus_channels = [];
            this.known_bus_events = [];
        },
        show_application: function() {
            this._super();
            this.start_polling();
        },
        on_logout: function() {
            var self = this;
            bus.bus.off('notification', this, this.bus_notification);
            _(this.known_bus_channels).each(function (channel) {
                bus.bus.delete_channel(channel);
            });
            _(this.known_bus_events).each(function(e) {
                self.bus_off(e[0], e[1]);
            });
            this._super();
        },
        start_polling: function() {
            this.declare_bus_channel();
            bus.bus.on('notification', this, this.bus_notification);
            bus.bus.start_polling();
        },
        bus_notification: function(notification) {
            var channel = notification[0];
            if (this.known_bus_channels.indexOf(channel) != -1) {
                var message = notification[1];
                bus.bus.trigger(channel, message);
            }
        },
        bus_on: function(eventname, eventfunction) {
            console.log(eventname, eventfunction)
            bus.bus.on(eventname, this, eventfunction);
            this.known_bus_events.push([eventname, eventfunction]);
        },
        bus_off: function(eventname, eventfunction) {
            bus.bus.on(eventname, this, eventfunction);
            var index = _.indexOf(this.known_bus_events, (eventname, eventfunction)); 
            this.known_bus_events.splice(index, 1);
        },
        /**
            must be overload
            openerp.web.WebClient.include({
                declare_bus_channel: function() {
                    this._super();
                    this.add_bus_channel('enhanced_bus');
                },
            });
        **/
        declare_bus_channel: function() {
        },
        add_bus_channel: function(channel) {
            if (this.known_bus_channels.indexOf(channel) == -1) {
                bus.bus.add_channel(channel);
                this.known_bus_channels.push(channel);
            }
        },
    });
});
