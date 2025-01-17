# Copyright (C) 2016-Today: La Louve (<http://www.lalouve.fr/>)
# @author: La Louve
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html

from datetime import date, datetime, timedelta
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.addons.queue_job.job import job

import logging
_logger = logging.getLogger(__name__)


class ShiftChangeTeam(models.Model):
    _name = "shift.change.team"
    _inherit = ['mail.thread']
    _order = "id desc"

    name = fields.Char(
        string="Name",
        compute="_compute_name_change_team",
        store=True,
        copy=False,
    )
    partner_id = fields.Many2one(
        'res.partner',
        string="Member",
        required=True,
    )
    current_shift_template_id = fields.Many2one(
        'shift.template',
        compute="_compute_mess_change_team",
        string="Current Team",
        store=True,
        copy=False,
    )
    next_current_shift_date = fields.Date(
        compute="_compute_mess_change_team",
        string='Next Shift with the Current Team',
        store=True,
    )
    new_shift_template_id = fields.Many2one(
        'shift.template',
        string="New Team",
        required=True,
    )
    is_abcd_to_abcd = fields.Boolean(
        compute="_compute_mess_change_team",
        string="Is ABCD to ABCD ?",
        store=True,
        default=False,
        copy=False,
    )
    first_next_shift_date = fields.Date(
        string="The date of first shift in new team",
    )
    second_next_shift_date = fields.Date(
        string="The date of second shift in new team",
    )
    full_seats_mess = fields.Html(
        compute="_compute_full_seats_massagess",
        string="Full Seats Messagess",
        store=True,
        copy=False,
    )
    is_full_seats_mess = fields.Boolean(
        compute="_compute_full_seats_massagess",
        string="Show full seats warning",
        store=True,
        copy=False,
    )
    new_next_shift_date = fields.Date(
        string="Start Date with the New Team",
        required=True,
    )
    mess_change_team = fields.Html(
        string='Message Change Team',
        compute='_compute_mess_change_team',
        store=True,
        copy=False,
    )
    is_mess_change_team = fields.Boolean(
        compute="_compute_mess_change_team",
        string="Show changing team messages",
        default=False,
        store=True,
        copy=False,
    )
    partner_state = fields.Selection([
        ('subscribed', 'Subscribed'), ('unsubscribed', 'Unsubscribed')],
        compute="_compute_mess_change_team",
        string="Current Team (state)",
        default='subscribed',
        store=True,
        copy=False,
    )
    show_partner_state = fields.Boolean(
        compute="_compute_mess_change_team",
        string="Show partner state",
        default=False,
        store=True,
        copy=False,
    )
    is_catch_up = fields.Boolean(
        string="Add a catch-up?",
        default=False,
        copy=False,
    )
    state = fields.Selection(
        [('draft', 'Draft'), ('closed', 'Closed')],
        string="Status",
        default="draft",
    )
    send_mail = fields.Boolean(
        string="Send Email Notification",
        default=True,
    )
    mail_template_id = fields.Many2one(
        "mail.template",
        string="Notification Email Template",
        help="If not set, the default change team notification will be sent",
        domain=[('model', '=', 'shift.change.team')],
        required=False,
    )
    shift_template_operation_id = fields.Many2one(
        "shift.template.operation",
        string="Template Operation",
        readonly=True,
        ondelete="set null",
        copy=False,
    )
    has_delayed_execution_errors = fields.Boolean(
        default=False,
        help="Technical field used by delayed execution.\n"
             "Instead of having the queue.job to stay in a failed state, "
             "we fail silently and check this box.\n\n"
             "This is used by the shift.template.operation model.",
        copy=False,
    )

    @api.multi
    @api.depends('partner_id')
    def _compute_name_change_team(self):
        for record in self:
            msg = _('Changes Team')
            record.name = '%s %s' % (record.partner_id.name, msg)

    @api.multi
    @api.constrains('current_shift_template_id', 'new_shift_template_id')
    def change_team_constraints(self):
        for record in self:
            if record.current_shift_template_id == \
                    record.new_shift_template_id:
                raise UserError(
                    _('The new team should be different the current team'))

    def _send_notification_email(self):
        mail_template_abcd = self.env.ref(
            'coop_membership.change_team_abcd_email')
        mail_template_ftop = self.env.ref(
            'coop_membership.change_team_ftop_email')
        # Hack to add attachments to the ftop email template
        # It should really be added in a data xml.. don't know why it's here
        if not mail_template_ftop.attachment_ids:
            mail_template_ftop.attachment_ids = [(6, 0, [
                self.env.ref('coop_membership.volant_sheet_attachment').id,
                self.env.ref('coop_membership.volant_calendar_attachment').id,
            ])]
        for rec in self.filtered('send_mail'):
            if self.mail_template_id:
                self.mail_template_id.send_mail(rec.id)
            else:
                if rec.new_shift_template_id.shift_type_id.is_ftop:
                    mail_template_ftop.send_mail(rec.id)
                else:
                    mail_template_abcd.send_mail(rec.id)

    @api.multi
    def button_close(self):
        # Only draft records
        self = self.filtered(lambda rec: rec.state == 'draft')
        # Only allow changes in members
        if any(not partner.is_member for partner in self.mapped('partner_id')):
            not_members = self.mapped('partner_id').filtered(
                lambda r: not r.is_member)
            raise UserError(_(
                "A person you want to change team must be a member:\n\n"
                "%s") % "\n".join(["* %s" % p.name for p in not_members]))
        # Process
        for record in self:
            if not self.env.context.get('skip_sanity_checks'):
                if record.is_mess_change_team or record.is_full_seats_mess:
                    raise UserError(_(
                        'There are some processes that were not done, '
                        'please do them first!'))
            # Do actual change
            record.set_in_new_team()
            record.state = 'closed'
            record.has_delayed_execution_errors = False
            # Handle Catch up mechanism
            if not record.new_shift_template_id.shift_type_id.is_ftop:
                if record.is_catch_up:
                    self.env['shift.counter.event'].sudo().with_context(
                        automatic=True,
                    ).create({
                        'name': _('Subtracted 1 point for changing team'),
                        'type': 'standard',
                        'partner_id': record.partner_id.id,
                        'point_qty': -1,
                    })
            # Handle delayed email notification
            if record.send_mail and not self.env.context.get('delay_email'):
                record._send_notification_email()
        # Handle delayed email notifications using queue job
        if self.env.context.get('delay_email'):
            records = self.filtered('send_mail')
            if records:
                records.with_delay()._job_send_notification_email()
        return True

    @api.multi
    def close_delayed(self):
        """ Schedules a queue job to close it """
        for rec in self:
            rec.with_delay()._job_validate_change_team()

    @api.multi
    def _create_registration_in_new_template(self, vals):
        """
        Helper method to create a new registration in the new template
        Automatically chooses the correct ticket.
        """
        self.ensure_one()
        # We use _search for performance
        shift_type = (
            self.new_shift_template_id.shift_type_id.is_ftop
            and 'ftop' or 'standard')
        shift_ticket_id = self.env['shift.template.ticket']._search([
            ('shift_template_id', '=', self.new_shift_template_id.id),
            ('shift_type', '=', shift_type),
            ], limit=1)[0]
        # Vals we know
        create_vals = {
            'partner_id': self.partner_id.id,
            'shift_template_id': self.new_shift_template_id.id,
            'shift_ticket_id': shift_ticket_id,
        }
        create_vals.update(vals)
        res = self.env['shift.template.registration.line'].create(create_vals)
        return res

    @api.multi
    def set_in_new_team(self):
        '''
            This method set partner on new team and the date of shifts
        '''
        self.ensure_one()
        current_registrations = \
            self.env['shift.template.registration.line'].search([
                ('partner_id', '=', self.partner_id.id),
                ('date_begin', '<=', self.new_next_shift_date),
                '|',
                ('date_end', '=', False),
                ('date_end', '>=', fields.Date.context_today(self)),
            ])
        future_registrations = \
            self.env['shift.template.registration.line'].search([
                ('partner_id', '=', self.partner_id.id),
                ('date_begin', '>', self.new_next_shift_date),
                ('date_begin', '>=', fields.Date.context_today(self)),
            ])
        new_leave_reg = None
        if current_registrations:
            previous_date_end = current_registrations[0].date_end
            # Finish the current line abruptely
            current_registrations[0].with_context(
                bypass_leave_change_check=True,
                creation_in_progress=True,
            ).write({
                'date_end': self.new_next_shift_date - timedelta(days=1),
            })
            # If our current registration is a leave,
            # we want to split it in two based on the date of next shift
            if current_registrations[0].leave_id:
                # Create a new one
                new_leave_reg = self._create_registration_in_new_template({
                    'date_begin': self.new_next_shift_date,
                    'date_end': previous_date_end,
                    'leave_id': current_registrations[0].leave_id.id,
                    'state': current_registrations[0].state,
                })
        # Add date begin into the first registration template in the future
        # Remove ALL Attendee on this template to create new Attendee on the
        # new team.
        # If doesn't have any templates in the future, create a new one
        if future_registrations:
            # If future registration is after a leave, we don't want to change
            # the registration date begin. Or if it's a future date.
            # we just want to remove it and create a new registration in
            # the new shift template
            if not new_leave_reg:
                future_registrations[0].with_context(
                    bypass_leave_change_check=True,
                ).write({'date_begin': self.new_next_shift_date})
            for registration in future_registrations:
                # Remove shift registrations
                registration.shift_registration_ids.unlink()
                # Store values that want to use to create the new one
                vals = registration.read([
                    'date_begin', 'date_end', 'leave_id', 'state'
                ])[0]
                # Use same registration as the new leave reg
                # Copying the behaviour before this patch
                if (
                    new_leave_reg
                    and registration.registration_id ==
                        current_registrations[0].registration_id
                ):
                    vals['registration_id'] = new_leave_reg.registration_id.id
                # We remove the registration line.
                # if there aren't any more registration lines in this reg,
                # also remove it
                reg_id = registration.registration_id
                registration.unlink()
                if not reg_id.line_ids:
                    reg_id.unlink()
                # Create a new registration in the new template
                self._create_registration_in_new_template(vals)
        elif not new_leave_reg:
            # We only create a new reg if it's not after a leave
            # because we might be dealing with a permanent leave,
            # and -in any case- we've already moved part of it.
            self._create_registration_in_new_template({
                'date_begin': self.new_next_shift_date,
            })

        # Set days of two next shifts
        date_future_shifts = self.env['shift.registration'].search([
            ('state', '=', 'open'),
            ('partner_id', '=', self.partner_id.id),
            ('date_begin', '>=', fields.Date.context_today(self)),
        ], limit=2).mapped('date_begin')

        # If we're in holidays and we didin't find next shifts
        # (not created yet) - Computed after the member returns
        if not date_future_shifts and new_leave_reg:
            if new_leave_reg.date_end:
                rec_dates = self.new_shift_template_id.get_recurrent_dates(
                    after=new_leave_reg.date_end,
                    before=new_leave_reg.date_end + timedelta(days=90),
                )
            else:
                # We're probably dealing with a permanent leave
                rec_dates = []
            date_future_shifts = rec_dates[:2]
        self.set_date_future_shifts(date_future_shifts)
        return True

    @api.multi
    def set_date_future_shifts(self, date_next_shifts):
        self.ensure_one()
        range_dates, list_dates = self.compute_range_day()
        if len(date_next_shifts) >= 2:
            self.first_next_shift_date = date_next_shifts[0].date()
            self.second_next_shift_date = date_next_shifts[1].date()
        elif len(date_next_shifts) == 1:
            self.first_next_shift_date = date_next_shifts[0].date()
            if list_dates:
                self.second_next_shift_date = list_dates[0].date()
        else:
            if list_dates:
                if len(list_dates) >= 1:
                    self.first_next_shift_date = list_dates[0].date()
                if len(list_dates) >= 2:
                    self.second_next_shift_date = list_dates[1].date()

    @api.multi
    @api.depends('new_shift_template_id')
    def _compute_full_seats_massagess(self):
        for record in self:
            shift_tmp = record.new_shift_template_id
            if shift_tmp and not shift_tmp.shift_type_id.is_ftop:
                available_standard_seat = 0
                for ticket in shift_tmp.shift_ticket_ids:
                    if ticket.shift_type == 'standard':
                        available_standard_seat += ticket.seats_available
                if available_standard_seat <= 0:
                    record.full_seats_mess = (_(
                        "There is no more seat in this " +
                        " team, would you like to continue?"))
                    record.is_full_seats_mess = True

    @api.multi
    def btn_full_seats_process(self):
        for record in self:
            record.is_full_seats_mess = False

    @api.multi
    def btn_change_team_process(self):
        for record in self:
            record.is_mess_change_team = False

    @api.multi
    def convert_state_partner(self):
        self.ensure_one()
        state = self.partner_id.cooperative_state
        if state == 'unsubscribed':
            return (_('Unsubscribed'))
        elif state == 'exempted':
            return (_('Exempted'))
        elif state == 'vacation':
            return (_('Vacation'))
        elif state == 'up_to_date':
            return (_('Up to date'))
        elif state == 'alert':
            return (_('Alert'))
        elif state == 'suspended':
            return (_('Suspended'))
        elif state == 'delay':
            return (_('Delay'))
        elif state == 'blocked':
            return (_('Blocked'))
        elif state == 'unpayed':
            return (_('Unpayed'))
        elif state == 'not_concerned':
            return (_('Not Concerned'))
        else:
            return ''

    @api.multi
    def convert_format_datatime(self, date_change):
        if date_change:
            if isinstance(date_change, str):
                date_change = fields.Date.from_string(date_change)
            if isinstance(date_change, date):
                return date_change.strftime('%d/%m/%Y')
        else:
            return ''

    @api.multi
    def compute_current_shift_template(self):
        self.ensure_one()
        if self.partner_id:
            # compute unsubscribed
            if self.partner_id.is_unsubscribed:
                self.partner_state = 'unsubscribed'
                self.show_partner_state = True
                if self.is_catch_up:
                    self.is_catch_up = False
            else:
                self.partner_state = 'subscribed'
                self.show_partner_state = False
            # compute next shift date
            reg = self.partner_id.tmpl_reg_ids.filtered(
                lambda r: r.is_current)
            if reg:
                self.current_shift_template_id = reg[0].shift_template_id
                next_shifts = \
                    self.current_shift_template_id.shift_ids.filtered(
                        lambda s: s.date_begin >= fields.Datetime.now())

                self.next_current_shift_date = next_shifts and \
                    next_shifts[0].date_begin.date() or False

    @api.multi
    def check_num_week(self, new_next_shift_date):
        """
        Gets the number of weeks that need to be substracted
        to synchronize with the new shift date
        """
        self.ensure_one()
        if isinstance(new_next_shift_date, datetime):
            new_next_shift_date = new_next_shift_date.date()
        get_param = self.env['ir.config_parameter'].sudo().get_param
        n_weeks_cycle = int(get_param('coop_shift.number_of_weeks_per_cycle'))
        week_number = \
            self.env['shift.template']._get_week_number(new_next_shift_date)
        week_difference = week_number - self.new_shift_template_id.week_number
        return week_difference % n_weeks_cycle

    @api.multi
    def compute_range_day(self):
        '''
        Compute range day base on next shift
        Range day is range of the last shift current team and the date
        of first shift on new team
        '''
        self.ensure_one()
        next_shifts = \
            self.current_shift_template_id.shift_ids.filtered(
                lambda s: s.date_begin < datetime.combine(
                    self.new_next_shift_date, datetime.min.time())).sorted(
                key=lambda l: l.date_begin, reverse=True)
        last_shift_date = next_shifts and next_shifts[0].date_begin or False
        new_team_start_date = fields.Datetime.from_string(
            self.new_next_shift_date).weekday()
        new_next_shift_date = self.new_next_shift_date
        if (
            new_team_start_date > 1
            and self.new_shift_template_id.shift_type_id.is_ftop
        ):
            new_next_shift_date = (
                fields.Datetime.from_string(self.new_next_shift_date)
                - timedelta(days=new_team_start_date)
            ).strftime('%Y-%m-%d')

        # This code to handle the rule that use to calculate
        # shifts in the future Making sure the calculation
        # is not miss any shifts I also get shifts in the
        # past and only choose shifts that are greater than
        # the start  date of new shift

        if not self.new_shift_template_id.shift_type_id.is_ftop:
            n_weeks_to_sync = self.check_num_week(new_next_shift_date)
            if n_weeks_to_sync != 0:
                new_next_shift_date = (
                    fields.Datetime.from_string(new_next_shift_date)
                    - timedelta(days=7 * n_weeks_to_sync)
                ).strftime('%Y-%m-%d')

        next_shift_mounth = (
            fields.Datetime.from_string(new_next_shift_date)
            + timedelta(days=90)
        ).strftime('%Y-%m-%d')

        rec_new_template_dates = \
            self.new_shift_template_id.get_recurrent_dates(
                new_next_shift_date, next_shift_mounth)

        for d in rec_new_template_dates:
            if d < datetime.combine(
                    self.new_next_shift_date, datetime.min.time()):
                rec_new_template_dates.remove(d)

        if rec_new_template_dates and last_shift_date:
            date_to_cal = last_shift_date
            if self.new_shift_template_id.shift_type_id.is_ftop:
                date_to_cal = self.new_next_shift_date
            range_dates = rec_new_template_dates[0] - \
                fields.Datetime.from_string(date_to_cal)
            return range_dates.days, rec_new_template_dates
        elif rec_new_template_dates and not last_shift_date:
            if self.new_shift_template_id.shift_type_id.is_ftop:
                range_dates = rec_new_template_dates[0] - \
                    fields.Datetime.from_string(self.new_next_shift_date)
                return range_dates.days, rec_new_template_dates
            else:
                return False, rec_new_template_dates
        else:
            return False, False

    @api.multi
    @api.depends('new_shift_template_id',
                 'new_next_shift_date', 'partner_id')
    def _compute_mess_change_team(self):
        for record in self:
            if not (record.current_shift_template_id.shift_type_id.is_ftop and
                    not record.new_shift_template_id.shift_type_id.is_ftop):
                record.compute_current_shift_template()
                if record.new_shift_template_id and record.new_next_shift_date:
                    range_dates, list_dates = record.compute_range_day()
                    if not record.current_shift_template_id.\
                            shift_type_id.is_ftop and \
                            not record.new_shift_template_id.\
                            shift_type_id.is_ftop:
                        if range_dates and range_dates > 40:
                            record.mess_change_team = (_("""
                            Il y a un écart de plus de 6
                            semaines entre le dernier service dans
                            l’ancienne équipe et le premier avec la nouvelle.
                            Souhaitez-vous continuer ?"""))
                            record.is_abcd_to_abcd = True
                            record.is_mess_change_team = True
                    elif record.new_shift_template_id.shift_type_id.is_ftop:
                        if range_dates <= 14:
                            record.mess_change_team = (_("""
                            La date de démarrage est inférieure à 15 jours
                            avant le jour de décompte volant qui suit.
                            Souhaitez-vous continuer ?"""))
                            record.is_mess_change_team = True

    @api.multi
    def unlink(self):
        if any([rec.state == 'closed' for rec in self]):
            raise ValidationError(_(
                "You can't delete a validated operation."))

    @job
    def _job_validate_change_team(self):
        """ Validate Shift Change Team """
        # We do it in a savepoint to avoid having the job stay in a failed state
        # In change, we set the has_delayed_execution_errors field to inform the
        # user as this job will never really fail.
        try:
            with self.env.cr.savepoint():
                self.with_context(delay_email=True).button_close()
        except Exception as e:
            self.write({'has_delayed_execution_errors': True})

    @job
    def _job_send_notification_email(self):
        """ Shift Change Team: Send notification email """
        self._send_notification_email()
