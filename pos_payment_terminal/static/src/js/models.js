odoo.define('pos_payment_terminal.models', function (require) {
    "use strict";

    var models = require('point_of_sale.models');
    models.load_fields('account.journal', ['pos_terminal_payment_mode']);

    var _paylineproto = models.Paymentline.prototype;
    models.Paymentline = models.Paymentline.extend({
        
        init_from_JSON: function (json) {
            _paylineproto.init_from_JSON.apply(this, arguments);
            this.payment_terminal_return_message = json.set_payment_terminal_return_message;
            this.cardholder_receipt = json.cardholder_receipt;
            this.merchant_receipt = json.merchant_receipt;
            this.card_name = json.card_name;
            this.tid = json.tid;
            this.receipt_number = json.receipt_number;
            this.trace_number = json.trace_number;           
        },
        export_as_JSON: function () {
           var vals = _paylineproto.export_as_JSON.apply(this, arguments)
           vals['payment_terminal_return_message'] = this.payment_terminal_return_message;
           vals['cardholder_receipt'] = this.cardholder_receipt;
           vals['merchant_receipt'] = this.merchant_receipt;
           vals['card_name'] = this.card_name;
           vals['tid'] = this.tid;
           vals['receipt_number'] = this.receipt_number;
           vals['trace_number'] = this.trace_number;
           return vals;
        },
        get_automatic_payment_terminal: function() {
            if (this.cashregister.journal.pos_terminal_payment_mode == 'card' && this.pos.config.iface_payment_terminal) {
                return true;
            }
            else {
                return false;
            }
        },
        set_payment_terminal_return_message: function(message) {
            this.order.assert_editable();
            this.payment_terminal_return_message = message;
            this.trigger('change',this);
        },
        set_card_name: function(card_name) {
            this.order.assert_editable();
            this.card_name = card_name;
            this.trigger('change',this);
        },
        set_tid: function(tid) {
            this.order.assert_editable();
            this.tid = tid;
            this.trigger('change',this);
        },
        set_receipt_number: function(receipt_number) {
            this.order.assert_editable();
            this.receipt_number = receipt_number;
            this.trigger('change',this);
        },
        set_trace_number: function(trace_number) {
            this.order.assert_editable();
            this.trace_number = trace_number;
            this.trigger('change',this);
        },
        set_cardholder_receipt: function(receipt_lines) {
            this.order.assert_editable();
            if (this.cardholder_receipt){
                this.cardholder_receipt += '<pre>';
            } else {
                this.cardholder_receipt = '<pre>';
            }
            this.cardholder_receipt += receipt_lines.join('</pre><pre>');
            this.cardholder_receipt += '</pre>';
            this.trigger('change', this);
        },
        set_merchant_receipt: function(receipt_lines) {
            this.order.assert_editable();
            if (this.merchant_receipt){
                this.merchant_receipt += '<pre>';
            } else {
                this.merchant_receipt = '<pre>';
            }
            this.merchant_receipt += receipt_lines.join('</pre><pre>');
            this.merchant_receipt += '</pre>';
            /*
            if (this.merchant_receipt){
                this.merchant_receipt += receipt_lines.join('<br />');
            } else {
                this.merchant_receipt = receipt_lines.join('<br />');
            }
            */
            this.trigger('change', this);
        },
    });

});
