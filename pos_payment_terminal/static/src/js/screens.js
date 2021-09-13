odoo.define('pos_payment_terminal.screens', function (require) {
    "use strict";

    var screens = require('point_of_sale.screens');

    screens.PaymentScreenWidget.include({
        render_paymentlines : function(){
            this._super.apply(this, arguments);
            var self  = this;
            var line = this.pos.get_order().selected_paymentline;

            if (line) {
                var auto = line.get_automatic_payment_terminal();

                if (auto) {
                    this.$('.paymentlines-container').unbind('click').on('click', '.payment-terminal-transaction-start', function(event){
                        $('.back').hide();
                        self.gui.show_popup('confirm',{
                            'title': _t('Please wait'),
                            'body':  _t('Please wait until the terminal transaction is completed'),
                            });
                        if (self.gui.current_popup) {
                            self.gui.current_popup.$('.button.confirm').css('display', 'none');
                        }
                        $('.delete-button').css('display', 'none');
                        $('.payment-terminal-transaction-start').css('display', 'none');
                        self.pos.proxy.payment_terminal_transaction_start(self, self.pos.currency.name);
                    });
                }
            }
        },
        click_paymentmethods: function() {
            var paymentlines = this.pos.get_order().get_paymentlines();
            if(paymentlines.length == 0){
                this._super.apply(this, arguments);
            } else {
                //Do nothing -> do not create new paymentline
            }
        },
        payment_input: function() {
            
            var self  = this;
            var line = this.pos.get_order().selected_paymentline;

            if (line) {
                var auto = line.get_automatic_payment_terminal();

                if (auto) {
                    //Do nothing -> prevent manual amount input
                } else {
                    this._super.apply(this, arguments);
                }
            }
        },
        click_numpad: function() {
            var paymentlines = this.pos.get_order().get_paymentlines();
            if(paymentlines.length == 0){
                //Do nothing -> do not create new paymentline
            } else {
                this._super.apply(this, arguments);
            }
        },
        transaction_error: function(message) {
            $('.back').show();
            $('.delete-button').css('display', 'block');
            $('.payment-terminal-transaction-start').css('display', 'inherit');
            this.gui.show_popup('error',{
                'title': _t('Transaction error'),
                'body':  message,
                });
            return;
        },
    });
});
