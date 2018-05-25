# -*- coding: utf-8 -*-
# © <2016> <CoÐoo Project, Lucas Huber, Vertel AB>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).
from odoo import models, fields, api
from datetime import date, datetime, timedelta
from odoo.exceptions import AccessError, UserError
import logging
_logger = logging.getLogger(__name__)


class ScrumSprint(models.Model):
    _name = 'project.scrum.sprint'
    _description = 'Project Scrum Sprint'
    _order = 'date_start desc'

    @api.one
    @api.onchange('project_id')
    def _compute_default_nr(self):
        sprints = self.search([('project_id', '=', self.project_id.id)])
        for record in sprints:
            sprint_nr = sprints.mapped('sprint_nr')
        new_nr = max(sprint_nr)
        self.sprint_nr = new_nr + 1
        return self.sprint_nr

    @api.one
    @api.onchange('project_id', 'sprint_nr')
    def _compute_default_nr_name(self):
        new_name = "%s Sprint %s" % (self.project_id.project_code, self.sprint_nr)
        self.name = new_name

    @api.multi
    @api.onchange('project_id')  # Sets default date_start
    def _compute_date_start(self):
        sprints = self.search([('project_id', '=', self.project_id.id)])
        for record in sprints:
            stop_date = sprints.mapped('date_stop')
        last_sprint_ends = max(stop_date)
        last_sprint_ends_d = fields.Date.from_string(last_sprint_ends)
        new_sprint_starts = (last_sprint_ends_d + timedelta(days=1))
        self.date_start = fields.Date.to_string(new_sprint_starts)

    @api.one
    @api.onchange('date_start')  # Sets default date_stop
    def onchange_date_stop(self):
        if self.date_start:
            if self.project_id:
                stop_date = fields.Date.from_string(self.date_start) + \
                                 timedelta(days=self.project_id.default_sprintlength - 1)
                self.date_stop = fields.Date.to_string(stop_date)
        else:
            pass

    @api.one
    @api.depends('date_start', 'date_stop')
    def _compute_length_days(self):
        if self.date_start and self.date_stop:
            self.sprint_length_days = (fields.Date.from_string(self.date_stop) -
                                       fields.Date.from_string(self.date_start)).days
        else:
            self.sprint_length_days = 0

    @api.depends('date_start', 'date_stop')
    def _compute_length_hrs(self):
        days = float(self.sprint_length_days)
        hrs = days * float(self.default_hrs)
        hrs_int = int(hrs)
        self.sprint_length_hrs = hrs_int
        return hrs_int

    @api.one  # TODO get available hours as default
    @api.depends('sprint_length_hrs', 'project_id')
    def _compute_av_hours(self):
        # self.ensure_one()
        hrs = float(self.sprint_length_hrs) or 0.0
        members = float(self.project_id.team_members) or 0.0
        available_hours = float(hrs * members) or 0.0
        self.available_hours = available_hours
        return available_hours

    @api.depends('date_start', 'date_stop')
    def _compute_length_week(self):
        self.sprint_length_week = (self.sprint_length_days + 1) / 7

    def _compute_length_txt(self):  # str(length_hrs + hrs + length_weeks + ' weeks')
        if self.date_start and self.date_stop:
            hrs = str(self.sprint_length_hrs)
            weeks = str(self.sprint_length_week)
            length_txt = str(hrs + ' hrs, ' + weeks + ' weeks')
            self.sprint_length_txt = length_txt
        else:
            self.sprint_length_txt = "undefined"

    @api.multi
    def _compute_spent_time_hrs(self):
        for record in self:
            if record.date_start and record.date_stop:
                if date.today() >= fields.Date.from_string(record.date_stop):
                    record.spent_hours = record.sprint_length_hrs
                else:
                    record.spent_hours = float((date.today() - fields.Date.from_string(record.date_start)).days) \
                        * record.default_hrs
            else:
                record.spent_hours = 0

    @api.multi
    def _compute_spent_time_proc(self):
        for record in self:
            if record.date_stop:
                if date.today() >= fields.Date.from_string(record.date_stop):
                    record.progress_time = 100.0
                else:
                    if record.sprint_length_days and record.spent_hours > 0.0:
                        spent_days = record.spent_hours / record.default_hrs
                        progresses = (spent_days / record.sprint_length_days) * 100
                        record.progress_time = progresses
                    else:
                        record.progress_time = 0.0

    def _compute_progress_task(self):
        for record in self:
            if record.planned_hours and record.effective_hours and record.planned_hours != 0:
                record.progress_tasks = record.effective_hours / record.planned_hours * 100
            else:
                record.progress_tasks = 0



    @api.multi
    @api.onchange('project_id')
    def _compute_def_scrum_master(self):
        for sprint in self:
            scrum_master = sprint.project_id.scrum_master_id
            sprint.scrum_master_id = scrum_master


    name = fields.Char(string='Sprint Name', required=True, default=_compute_default_nr_name, size=60)
    sprint_nr = fields.Integer(string='Sprint number',  store=True)
    meeting_ids = fields.One2many(comodel_name='project.scrum.meeting', inverse_name='sprint_id',
                                  string='Meetings')
    meeting_dm_ids = fields.One2many(comodel_name='project.scrum.meeting', inverse_name='sprint_dm_id',
                                     string='Daily Scrum')
    meeting_p_id = fields.Many2one(comodel_name="project.scrum.meeting",
                                   string="Planning Meeting")  # TODO domain search in planning
    meeting_rev_id = fields.Many2one(comodel_name="project.scrum.meeting",
                                     string="Sprint Review")  # TODO domain search in Reviews
    meeting_retro_id = fields.Many2one(comodel_name="project.scrum.meeting", string="Sprint Retrospective")
    user_id = fields.Many2one(comodel_name='res.users', string='Assigned to')
    date_start = fields.Date(string='Starting Date')
    date_stop = fields.Date(string='Ending Date')
    sprint_length_txt = fields.Text(compute='_compute_length_txt', string='Sprint length defined',
                                    help="Calculated sprint length")
    sprint_length_hrs = fields.Integer(compute='_compute_length_hrs', string='Sprint length(in hrs)', store=True)
    sprint_length_days = fields.Integer(compute='_compute_length_days', string='Sprint length(in days)', store=True)
    sprint_length_week = fields.Integer(compute='_compute_length_week', string='Sprint length(in weeks)', store=False)
    spent_hours = fields.Integer(compute='_compute_spent_time_hrs', string='Spent time (hrs)', store=False,
                                 help="Spent Sprint time in hours")
    progress_time = fields.Float(compute="_compute_spent_time_proc", group_operator="avg", type='float',
                                 multi="progress_time", string='Spent Time (%)',
                                 help="Computed as: Time Spent / Total Time.")
    progress_tasks = fields.Float(compute="_compute_progress_task", group_operator="avg", type='float',
                                  multi="progress_tasks", string='Progress in Tasks (%)',
                                  help="Computed as: Time Spent / Total Time.")
    description = fields.Text(string='Description', required=False)
    project_id = fields.Many2one(comodel_name='project.project', string='Project', ondelete='set null', select=True,
                                 track_visibility='onchange', change_default=True, required=True,
                                 help="If you have [?] in the project name, it means there "
                                      "are no analytic account linked to this project.")
    product_owner_id = fields.Many2one(comodel_name='res.users', string='Product Owner',
                                       required=False, help="The person who is responsible for the product")
    scrum_master_id = fields.Many2one(comodel_name='res.users', string='Scrum Master',
                                      default=_compute_def_scrum_master,
                                      required=False, help="The person who maintains the processes for the product")
    sprint_us_ids = fields.Many2many(comodel_name='project.scrum.us', string='User Stories')
    def_o_done_ids = fields.Many2many(comodel_name="project.scrum.def_done", inverse_name='sprint_ids',
                                      string="Def. of Done")
    issue_ids = fields.One2many('project.issue', 'sprint_id', string="Issues",
                                domain=[('stage_id.fold', '=', False)])
    task_ids = fields.One2many('project.task', 'sprint_id', string="Tasks")
    user_story_count = fields.Integer(compute='_user_story_count', string="User Stories")
    task_active_count = fields.Integer(compute='_task_active_count', string="Active Tasks")
    task_p_backlog_count = fields.Integer(compute='_task_p_backlog_count', string="P.Backlog")
    task_s_backlog_count = fields.Integer(compute='_task_s_backlog_count', string="S.Backlog")
    def_o_done_count = fields.Integer(compute='_def_o_done_count', string="Def. of Done")
    issue_count = fields.Integer(compute='_issue_count', string="Impediments")
    meeting_count = fields.Integer(compute='_meetings_count', string="Meetings")
    planning_agenda = fields.Html(related='meeting_p_id.agenda', string='Sprint Planning')
    review_agenda = fields.Html(related='meeting_rev_id.agenda', string='Sprint Review')
    retrospective_agenda = fields.Html(related='meeting_retro_id.agenda', string='Sprint Retrospective')
    sequence = fields.Integer('Sequence', help="Gives the sequence order when displaying a list of tasks.")

    available_hours = fields.Float(compute='_compute_av_hours', store=True, multi="available_hours", string='Available Hours',
                                   help='Calculated or estimated total of Team working hours for this sprint.'
                                        ' (usually set by team during sprint planning)'
                                        ' (calculated by Nr of team members x sprint length in hrs)')
    planned_hours = fields.Float(compute="_compute_pl_hours", store=False, multi="planned_hours", string='Planned Hours',
                                 help='Calculated time to do the tasks for this sprint.'
                                      ' (Total of all tasks in sprint)')
    effective_hours = fields.Float(compute="_compute_eff_hours", multi="effective_hours", store=True,
                                   string='Effective Hours', help="Computed using the sum of the tasks work done.")
    state = fields.Selection([('draft', 'Draft'),
                              ('open', 'Current'),
                              ('cancel', 'Cancelled'),
                              ('done', 'Done')],
                             string='State', default='draft', required=False)
    company_id = fields.Many2one(related='project_id.analytic_account_id.company_id')
    default_hrs = fields.Float(related='project_id.default_hrs', string='Default daily hours')

    _sql_constraints = [
        ('sprint_nr_unique',
         'UNIQUE (project_id, sprint_nr)',
         'Only one sprint with the same number allowed!')]

    @api.one
    @api.constrains('date_stop')
    def _check_date(self):
        """
        Prevents the user to create a sprint in the past fields.Date.from_string(self.date_start)
        """
        date_stop = fields.Date.from_string(self.date_stop)
        date_today = fields.Date.from_string(fields.Date.context_today(self))
        if (date_stop < date_today):
            raise UserError("The date of your sprint is in the past.")

    @api.one  # Getting the current id from sprint (creepy method)
    @api.onchange('meeting_ids.meeting_type')
    def _get_current_id(self):
        meeting_type = self.meeting_ids.meeting_type
        meeting_id = self.meeting_ids.id
        if meeting_type == "planning":  # Sprint Planning Items
            pass
            # ids_meetings_current = self.env['project.scrum.meeting'].search([('sprint_id', '=', self.id)])
            # ids_meetings_current = sprint.mapped('meeting_ids')
            # id_meeting_current = ids_meetings_current.search([('meeting_type', '=', self.meeting_type)])

        #  self.meeting_p_id = self._get_current_id()  # TODO Setting the Planning many2one field in sprint does not work. self.id?

    # **** Calculating of number of items ****
    def _user_story_count(self):    # method that calculate how many user stories exist
        for p in self:
            p.user_story_count = len(p.sprint_us_ids)

    @api.depends('task_ids')
    def _task_active_count(self):  # method that calculate how many tasks exist
        tasks = self.env['project.task'].search([('sprint_id', '=', self.id), ('stage_id.scrum_stages', '=', "progress")])
        for p in self:
            p.task_active_count = len(tasks)

    def _task_p_backlog_count(self):    # method that calculate how many tasks in sprint backlog exists
        tasks = self.env['project.task'].search([('sprint_id', '=', self.id), ('stage_id.scrum_stages', '=', "pbacklog")])
        for p in self:
            p.task_p_backlog_count = len(tasks)

    def _task_s_backlog_count(self):    # method that calculate how many tasks in sprint backlog exists
        tasks = self.env['project.task'].search([('sprint_id', '=', self.id), ('stage_id.scrum_stages', '=', "sbacklog")])
        for p in self:
            p.task_s_backlog_count = len(tasks)

    def _meetings_count(self):    # method that calculate how many meetings exists
        for p in self:
            p.meeting_count = len(p.meeting_ids)

    def _def_o_done_count(self):    # method that calculate how many Def of Done exist
        for p in self:
            p.def_o_done_count = len(p.def_o_done_ids)

    def _issue_count(self):    # method that calculate how many Issues exist
        for p in self:
            p.issue_count = len(p.issue_ids)



    # @api.depends('task_ids', 'available_hours')
    @api.one
    def _compute_pl_hours(self):
        planned_hours = 0.0
        for task in self.task_ids:
            planned_hours += task.planned_hours or 0.0
        self.planned_hours = planned_hours
        return True

    @api.depends('task_ids')
    def _compute_eff_hours(self):
        effective_hours = 0.0
        for task in self.task_ids:
            effective_hours += task.effective_hours or 0.0

        self.effective_hours = effective_hours
        return True

    # creating/deleting Meetings items for sprint (meeting_type = sprint)
    @api.multi  # TODO Does not work, does not get active onchange 'state'?
    @api.depends('state')
    def _onchange_state_time(self):
        if self.state == "open":  # Sprint Opened

            self.env['project.scrum.meeting'].create({'allday': True,
                                                      'project_id': self.project_id.id,
                                                      # 'sprint_id': self.id,
                                                      'meeting_type': "sprint",
                                                      'start_date': self.date_start,
                                                      'stop_date': self.date_stop,
                                                      'start_datetime': self.date_start,
                                                      'stop_datetime': self.date_stop,
                                                      'state': "sent",
                                                      'name': "%s - %s" % (self.name, self.date_start)
                                                      })
        elif self.state == "draft":  # Sprint Draft
            pass
        elif self.state == "cancel":  # Sprint Canceled
            pass
        elif self.state == "done":  # Sprint done
            pass
        else:
            pass

    @api.multi  # Cron function to adjust the state of the sprints
    def run_sprint_state(self):
        for record in self:
            if record.date_stop and record.date_start and record.state != "cancel":
                if fields.Date.from_string(record.date_start) >= date.today():
                    record.state = "draft"
                elif fields.Date.from_string(record.date_start) <= date.today() and\
                     fields.Date.from_string(record.date_stop) >= date.today():
                    record.state = "open"
                elif fields.Date.from_string(record.date_stop) <= date.today():
                    record.state = "done"

