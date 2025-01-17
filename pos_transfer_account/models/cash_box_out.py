# -*- coding: utf-8 -*-
# Copyright (C) 2016-Today: La Louve (<http://www.lalouve.net/>)
# @author: Sylvain LE GAL (https://twitter.com/legalsylvain)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, models


class CashBoxOut(models.TransientModel):
    _inherit = 'cash.box.out'

    @api.multi
    def _calculate_values_for_statement_line(self, record):
        session_obj = self.env['pos.session']
        active_model = self._context.get('active_model', False)
        active_ids = self._context.get('active_ids', [])

        # Call with [0] because new api.one func calls old api func
        res = super(CashBoxOut, self)._calculate_values_for_statement_line(
            record)

        if active_model == 'pos.session':
            session = session_obj.browse(active_ids[0])
            if session.config_id.transfer_account_id:
                res['account_id'] =\
                    session.config_id.transfer_account_id.id

        return res
