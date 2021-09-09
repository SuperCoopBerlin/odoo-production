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
from odoo import models, fields


class AccountBankStatementLine(models.Model):
    _inherit = 'account.bank.statement.line'

    payment_terminal_return_message = fields.Char(
        string='payment terminal return message'
    )
    merchant_receipt = fields.Html(string='Merchant receipt')
    cardholder_receipt = fields.Html(string='Cardholder receipt')

    card_name = fields.Char(string='Card name')
    tid = fields.Char(string='Terminal ID')
    receipt_number = fields.Char(string='Receipt number')
    trace_number = fields.Char(string='Trace number')
