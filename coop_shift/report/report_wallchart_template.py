# Copyright (C) 2016-Today: La Louve (<http://www.lalouve.net/>)
# Copyright (C) 2019-Today: Druidoo (<https://www.druidoo.io>)
# @author Julien WESTE
# @author Sylvain LE GAL (https://twitter.com/legalsylvain)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from datetime import timedelta, date, datetime

from odoo import api, models, fields, _

from .report_wallchart_common import rounding_limit

WEEK_DAYS = {
    'mo': _('Monday'),
    'tu': _('Tuesday'),
    'we': _('Wednesday'),
    'th': _('Thursday'),
    'fr': _('Friday'),
    'sa': _('Saturday'),
    'su': _('Sunday'),
}

weekday_list = ["mo", "tu", "we", "th", "fr", "sa", "su", ]


class ReportWallchartTemplate(models.AbstractModel):
    _name = 'report.coop_shift.report_wallchart_template'
    _inherit = 'report.coop_shift.report_wallchart_common'

    @api.model
    def _get_ticket_partners(self, ticket):
        partners = []
        future_seats = 0
        for reg in ticket.registration_ids:
            ok = False
            dates = ""
            for line in reg.line_ids:
                if (line.date_end and fields.Date.from_string(
                        line.date_end) <= date.today()) or\
                        line.state != "open":
                    continue
                ok = True
                if line.date_begin and fields.Date.from_string(
                        line.date_begin) > date.today():
                    date_begin = datetime.strftime(fields.Date.from_string(
                        line.date_begin) - timedelta(days=1), "%x")
                    dates = ("+ until %s " % date_begin) + dates
                    future_seats += 1
                if line.date_end:
                    date_end = datetime.strftime(fields.Date.from_string(
                        line.date_end) + timedelta(days=1), "%x")
                    dates = ("+ from %s " % date_end) + dates
                    future_seats -= 1
            dates = dates and (" (" + dates[2:-1] + ")")
            if ok:
                partners.append({
                    'partner_id': reg.partner_id,
                    'dates': dates})
        return partners, future_seats

    @api.model
    def _get_tickets(
            self, template,
            product_name='coop_shift.product_product_shift_standard'):
        product_name = 'coop_shift.product_product_shift_standard'
        return super(ReportWallchartTemplate, self)._get_tickets(
            template, product_name)

    @api.model
    def _get_template_info(self, template):
        tickets = self._get_tickets(template)
        partners = []
        seats_max = 0
        future_seats = 0
        for ticket in tickets:
            p, f = self._get_ticket_partners(ticket)
            partners += p
            future_seats += f
            seats_max += ticket.seats_max
        return partners, seats_max, future_seats

    @api.model
    def _get_templates(self, data):
        final_result = []
        for week_day in data.keys():
            if week_day == "id" or not data.get(week_day, False):
                continue

            result = []
            sql = """SELECT start_time, end_time
                FROM shift_template
                WHERE %s is True
                GROUP BY start_time, end_time
                ORDER BY start_time
            """
            self.env.cr.execute(sql, week_day)

            for t in self.env.cr.fetchall():
                res = {}
                res['start_time'] = self.format_float_time(t[0])
                res['end_time'] = self.format_float_time(t[1])
                base_search = [
                    ('start_time', '>=', t[0] - rounding_limit),
                    ('start_time', '<=', t[0] + rounding_limit),
                    ('end_time', '>=', t[1] - rounding_limit),
                    ('end_time', '<=', t[1] + rounding_limit),
                    ('week_list', '=', week_day.upper()),
                ]
                week_letters = ['A', 'B', 'C', 'D']
                for week in [1, 2, 3, 4]:
                    template = self.env['shift.template'].search(
                        base_search + [('week_number', '=', week)])
                    if not template:
                        res['partners' + week_letters[week - 1]] = []
                        res['free_seats' + week_letters[week - 1]] = 0
                        continue
                    template = template[0]
                    partners, seats_max, future_seats =\
                        self._get_template_info(template)
                    res['partners' + week_letters[week - 1]] = partners
                    res['free_seats' + week_letters[week - 1]] =\
                        max(0, seats_max - len(partners))

                contain_data_in_period = any(
                    len(res.get('partners' + week_letter, [])) > 0 and
                    any(
                        partner['dates'] != ''
                        for partner in res.get('partners' + week_letter, [])
                    )
                    for week_letter in week_letters
                )
                if contain_data_in_period:
                    result.append(res)
            if result:
                final_result.append({
                    'day': WEEK_DAYS[week_day],
                    'next_dates': self._get_next_dates(
                        weekday_list.index(week_day)),
                    'times': result
                })
        return final_result

    @api.model
    def _get_next_dates(self, weekday):
        result = {}
        today = date.today()
        next_date = today + timedelta(days=(weekday - today.weekday()) % 7)
        week_number = self._get_week_number(next_date)
        for i in range(4):
            delta = (i + 1 - week_number[0]) % 4
            result["week" + ["A", "B", "C", "D"][i]] =\
                "(%s, %s, %s, %s, %s, %s, %s, ...)" % (
                    datetime.strftime(
                        next_date + timedelta(weeks=delta), "%d/%m"),
                    datetime.strftime(
                        next_date + timedelta(weeks=delta + 4), "%d/%m"),
                    datetime.strftime(
                        next_date + timedelta(weeks=delta + 8), "%d/%m"),
                    datetime.strftime(
                        next_date + timedelta(weeks=delta + 12), "%d/%m"),
                    datetime.strftime(
                        next_date + timedelta(weeks=delta + 16), "%d/%m"),
                    datetime.strftime(
                        next_date + timedelta(weeks=delta + 20), "%d/%m"),
                    datetime.strftime(
                        next_date + timedelta(weeks=delta + 24), "%d/%m"),)
        return result

    @api.model
    def _get_report_values(self, docids, data=None):
        self.model = self.env.context.get('active_model')
        docs = {}
        docs['Wallcharts'] = self._get_templates(data['form'])
        return {
            'doc_ids': self.ids,
            'partner_id': self.env.user.partner_id,
            'doc_model': self.model,
            'data': data['form'],
            'docs': docs,
            'date': date,
        }
