odoo.define('pos_payment_terminal.devices', function (require) {
    "use strict";

    var devices = require('point_of_sale.devices');
    var utils = require('web.utils');
    var round_pr = utils.round_precision;

    devices.ProxyDevice.include({
        wait_terminal_answer: function(cashregister) {
            if (this.pos.config.iface_payment_terminal_return) {
                return true;
            }
            return false;
        },
        get_data_send: function(order, line, currency_iso) {
            var data = {
                    'amount' : order.get_due(line),
                    'currency_iso' : currency_iso,
                    'payment_mode' : line.cashregister.journal.pos_terminal_payment_mode,
                    'wait_terminal_answer' : this.wait_terminal_answer(),
                    };
            return data;
        },

        payment_terminal_transaction_start: function(screen, currency_iso){
            var self = this;
            var order = this.pos.get_order();
            var line = order.selected_paymentline;
            var data = self.get_data_send(order, line, currency_iso);
            if (this.wait_terminal_answer()) {
                screen.$('.delete-button').css('display', 'none');

                //this.message('payment_terminal_transaction_start_with_return', {'payment_info' : JSON.stringify(data)}, { timeout: 240000 }).then(function (answer) { 
                    //console.log(answer)
                        var answer = 
                        {
                        "pos_number": "xxxxxxxx",
                        "transaction_result": 0,
                        "amount_msg": "000000000100",
                        "payment_mode": "Girocard",
                        "payment_terminal_return_message": {
                            "result_code": [
                            0
                            ],
                            "amount": "000000000100",
                            "currency_code": "0978",
                            "trace_number": "000052",
                            "time": "081836",
                            "date_day": "0827",
                            "tid": "xxxxxxxx",
                            "card_number": "H%\u0011\u0000\u0010`B\u0013u?",
                            "card_sequence_number": "0000",
                            "receipt": "0031",
                            "aid": [
                            54,
                            56,
                            53,
                            55,
                            56,
                            49,
                            0,
                            0
                            ],
                            "type": [
                            112
                            ],
                            "card_expire": "2212",
                            "card_type": [
                            5
                            ],
                            "card_name": "Girocard",
                            "additional": "Autorisierung erfolgt",
                            "turnover": "000031",
                        },
                        "merchant_receipt": [
                            "* *  Händlerbeleg  * *",
                            "SuperCoop Berlin eG",
                            "Oudenarder Straße 16",
                            "13347 Berlin",
                            "supercoop.de",
                            "Datum:            27.08.2021",
                            "Uhrzeit:        08:18:36 Uhr",
                            "Beleg-Nr.               0031",
                            "Trace-Nr.             000052",
                            "Kartenzahlung",
                            "kontaktlos",
                            "girocard",
                            "Nr. ###############3753 0000",
                            "gültig bis             12/22",
                            "Genehmigungs-Nr.      xxxxxx",
                            "Terminal-ID         xxxxxxxx",
                            "Pos-Info           00 075 00",
                            "AS-Zeit 27.08.     08:18 Uhr",
                            "Weitere Daten /00000xxxxx//A",
                            "000000xxx/020xxx/",
                            "Betrag EUR              1,00",
                            "Autorisierung erfolgt",
                            "Bitte Beleg aufbewahren",
                        ],
                        "cardholder_receipt": [
                            "* *  Kundenbeleg  * *",
                            "SuperCoop Berlin eG",
                            "Oudenarder Straße 16",
                            "13347 Berlin",
                            "supercoop.de",
                            "Datum:            27.08.2021",
                            "Uhrzeit:        08:18:36 Uhr",
                            "Beleg-Nr.               0031",
                            "Trace-Nr.             000052",
                            "Kartenzahlung",
                            "kontaktlos",
                            "girocard",
                            "Nr. ###############3753 0000",
                            "gültig bis             12/22",
                            "Genehmigungs-Nr.      xxxxxx",
                            "Terminal-ID         xxxxxxxx",
                            "Pos-Info           00 075 00",
                            "AS-Zeit 27.08.     08:18 Uhr",
                            "Weitere Daten /00000xxxxx//A",
                            "000000xxx/020xxx/",
                            "Betrag EUR              1,00",
                            "Autorisierung erfolgt",
                            "Bitte Beleg aufbewahren",
                        ]
                        }
                        console.log(answer)
                    if (answer) {
                        var transaction_result = answer['transaction_result'];
                        if (transaction_result == '0') {
                            // This means that the operation was a success
                            // We get amount and set the amount in this line
                            var rounding = self.pos.currency.rounding;
                            var amount_in = round_pr(answer['amount_msg'] / 100, rounding);
                            //var amount_in = answer['amount_msg'] / 100;
                            if (!amount_in == 0) {
                                line.set_amount(amount_in);
                                if ('payment_terminal_return_message' in answer) {
                                    line.set_payment_terminal_return_message(answer.payment_terminal_return_message);
                                }
                                //Set receipt info
                                if ('cardholder_receipt' in answer) {
                                    line.set_cardholder_receipt(answer.cardholder_receipt);
                                }
                                screen.order_changes();
                                if(screen.setup_auto_validation_timer !== undefined) {
                                    screen.setup_auto_validation_timer();
                                }
                                // screen.render_paymentlines();
                                var amount_in_formatted = screen.format_currency_no_symbol(amount_in);
                                screen.$('.paymentline.selected .edit').text(amount_in_formatted);
                                screen.$('.delete-button').css('display', 'none');
                                //screen.$('.automatic-cashdrawer-transaction-start').css('display', 'none');
                            }
                        } else {
                            screen.transaction_error();
                            screen.$('.delete-button').css('display', 'block');
                            //$('.back').show();
                        }
                    } else {
                        screen.transaction_error();
                        screen.$('.delete-button').css('display', 'block');
                    }
                //});
            } else {
                this.message('payment_terminal_transaction_start', {'payment_info' : JSON.stringify(data)});
            }
        },
    });
});
