##############################################################################
#
#    POS Payment Terminal module for Odoo
#    Copyright (C) 2014 Aurélien DUMAINE
#    Copyright (C) 2015 Akretion (www.akretion.com)
#    Copyright (C) 2020-Today: Druidoo (<https://www.druidoo.io>)
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
import logging

from odoo import api, models
from odoo.tools.float_utils import float_compare

_logger = logging.getLogger(__name__)


class PosOrder(models.Model):
    _inherit = 'pos.order'

    @api.model
    def _payment_fields(self, ui_paymentline):
        fields = super(PosOrder, self)._payment_fields(ui_paymentline)

        fields.update({
            'payment_terminal_return_message': ui_paymentline.get(
            'payment_terminal_return_message'),
            'card_name': ui_paymentline.get('card_name'),
            'tid': ui_paymentline.get('tid'),
            'receipt_number': ui_paymentline.get('receipt_number'),
            'trace_number': ui_paymentline.get('trace_number'),
            'merchant_receipt': ui_paymentline.get('merchant_receipt'),
            'cardholder_receipt': ui_paymentline.get('cardholder_receipt')
        })

        return fields

    def add_payment(self, data):
        statement_id = super(PosOrder, self).add_payment(data)
        statement_lines = self.env['account.bank.statement.line'].search([('statement_id', '=', statement_id),
                                                                         ('pos_statement_id', '=', self.id),
                                                                         ('journal_id', '=', data['journal'])])
        statement_lines = statement_lines.filtered(lambda line: float_compare(line.amount, data['amount'],
                                                                              precision_rounding=line.journal_currency_id.rounding) == 0)

        for line in statement_lines:
            if not line.payment_terminal_return_message:
                line.payment_terminal_return_message = data.get('payment_terminal_return_message')
                line.card_name = data.get('card_name')
                line.tid = data.get('tid')
                line.receipt_number = data.get('receipt_number')
                line.trace_number = data.get('trace_number')
                line.merchant_receipt = data.get('merchant_receipt')
                line.cardholder_receipt = data.get('cardholder_receipt')
                break

        return statement_id
