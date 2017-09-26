# -*- coding: utf-8 -*-
# © <2016> <CoÐoo Project, Lucas Huber, Vertel AB>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).
from odoo import models, fields, api
# import openerp.tools
import math
import re
from datetime import date, datetime, timedelta
import logging
_logger = logging.getLogger(__name__)


class ScrumUserStories(models.Model):

    _name = 'project.scrum.us'
    _description = 'Project Scrum Use Stories'
    _order = 'sequence'

    @api.model
    def _read_group_stage_ids(self, present_ids, domain, **kwargs):
        project_id = self._resolve_project_id_from_context()
        result = self.env['project.task.type'].search([('project_ids', '=', project_id)]).name_get()
        return result, None

    _group_by_full = {
        'stage_id': _read_group_stage_ids,
        }

    name = fields.Char(string='User Story', required=True)
    color = fields.Integer('Color Index')
    sequence = fields.Integer('Sequence')
    description = fields.Html(string='Description')
    description_short = fields.Text(compute='_conv_html2text', store=True)
    actor_ids = fields.Many2many(comodel_name='project.scrum.actors', string='Actors')
    project_id = fields.Many2one(comodel_name='project.project', string='Project', ondelete='set null',
                                 select=True, track_visibility='onchange', change_default=True)
    sprint_ids = fields.Many2many(comodel_name='project.scrum.sprint', string='Sprints')
    stage_id = fields.Many2one(comodel_name='project.task.type', string='Stage',
                               track_visibility='onchange', select=True,
                               domain="[('project_ids', '=', project_id)]", copy=False)
    task_ids = fields.One2many(comodel_name='project.task', inverse_name='task_us_ids')
    task_def_done_ids = fields.One2many(comodel_name='project.scrum.def_done', string='Def. of Done',
                                        inverse_name='user_story_id')
    task_count = fields.Integer(compute='_task_count', string='Related Tasks', store=True)  # Store True does not work
    def_done_ids = fields.One2many(comodel_name='project.scrum.def_done', inverse_name='user_story_id')
    def_done_count = fields.Integer(compute='_def_done_count', store=True)
    partner_ids = fields.Many2many(comodel_name='res.partner', string='Stakeholders',
                                   help="Which partners shares interest and influences this Story?")
    company_id = fields.Many2one(related='project_id.analytic_account_id.company_id')

    @api.depends('description')
    def _conv_html2text(self):  # method that return a short text from description of user story
        self.description_short = re.sub('<.*?>', ' ', self.description)
        if len(self.description_short)>= 150:
            self.description_short = self.description_short[:149]

    @api.depends('task_ids')
    def _task_count(self):    # method that calculate how many tasks exist
        for p in self:
            p.task_count = len(p.task_ids)

    @api.depends('def_done_ids')
    def _def_done_count(self):    # method that calculate how many def of done exist
        for p in self:
            p.def_done_count = len(p.def_done_ids)

    def _resolve_project_id_from_context(self, cr, uid, context=None):
        """ Returns ID of project based on the value of 'default_project_id'
            context key, or None if it cannot be resolved to a single
            project.
        """
        if context is None:
            context = {}
        if type(context.get('default_project_id')) in (int, long):
            return context['default_project_id']
        if isinstance(context.get('default_project_id'), basestring):
            project_name = context['default_project_id']
            project_ids = self.pool.get('project.project').name_search(cr, uid, name=project_name, context=context)
            if len(project_ids) == 1:
                return project_ids[0][0]
        return None


class ScrumActors(models.Model):
    _name = 'project.scrum.actors'
    _description = 'Actors in user stories'

    name = fields.Char(string='Name', size=60)


class ScrumMeeting(models.Model):
    _name = 'project.scrum.meeting'
    _description = 'Project Scrum Meetings'
    _inherit = ['mail.thread', 'ir.needaction_mixin']

    project_id = fields.Many2one(comodel_name='project.project',  string='Project', default='_get_project_id',
                                 ondelete='set null', select=True, track_visibility='onchange', change_default=True)
    name = fields.Char(string='Meeting', size=60)
    sprint_id = fields.Many2one(comodel_name='project.scrum.sprint', inverse_name='meeting_ids', string='Sprint',
                                track_visibility='onchange')
    sprint_dm_id = fields.Many2one(comodel_name='project.scrum.sprint', inverse_name='meeting_dm_ids',
                                   string='Sprint Daily Meeting', track_visibility='onchange')
    meeting_type = fields.Selection([
        ('daily', 'Daily Scrum'),
        ('planning', 'Sprint Planning'),
        ('review', 'Sprint Review'),
        ('retro', 'Sprint Retrospective'),
        ('sprint', 'Sprint'),
        ('other', 'Other Meetings')
        ],
        string='Meeting Type', required=True, default='other')
    state = fields.Selection([('draft', 'Unconfirmed'),
                              ('sent', 'Sent'),
                              ('done', 'Done')],
                             string='Status', default='draft', readonly=False, track_visibility='onchange')
    allday = fields.Boolean('All Day', state={'done': [('readonly', True)]})
    start_datetime = fields.Datetime(string='Start DateTime', required=True,
                                     track_visibility='onchange', default=datetime.now())
    start_date = fields.Date('Start Date', state={'done': [('readonly', True)]}, track_visibility='onchange')
    stop_datetime = fields.Datetime('Ends at', readonly=False, track_visibility='onchange')
    stop_date = fields.Date('End Date', state={'done': [('readonly', True)]}, track_visibility='onchange')
    duration = fields.Float(string='Duration', default=1.0, track_visibility='onchange')
    user_id_meeting = fields.Many2one(comodel_name='res.users', string='Responsible Person', required=True,
                                      default=lambda self: self.env.user)
    agenda = fields.Html(string='Meeting Agenda', required=False,
                         help="Agenda for this meeting")
    protocol = fields.Html(string='Meeting Outcome', required=False,
                           help="Protocol for this meeting")
    description = fields.Text(string='Description', required=False)
    question_backlog = fields.Selection([('yes', 'Yes'), ('no', 'No')], string='Backlog Accurate?',
                                        required=False, default='yes')
    company_id = fields.Many2one(related='project_id.analytic_account_id.company_id', string='Company Analytic Account')
    issue_ids = fields.Many2many(comodel_name='project.issue', string='Impediments / Issues')

    _sql_constraints = [
        ('meetings_unique',
         'UNIQUE (start_datetime, sprint_id)',
         'Only one meeting at the same time item is allowed per sprint and day!')]

    @api.one  # TODO Getting the Project id, find a better method eg. include project_id in context?
    @api.onchange('sprint_id')
    def _get_project_id(self):
        if self.sprint_id:
            self.project_id = self.sprint_id.project_id

    @api.multi  # Getting the Start DateTime
    def _compute_start_time_hrs(self, meeting_type):
        self.ensure_one()  # One record expected, raise error if self is an unexpected recordset
        meeting_ids = self.search([('meeting_type', '=', meeting_type), ('project_id', '=', self.project_id.id)])
        if meeting_ids:
            for record in meeting_ids:
                start_datetime_list = meeting_ids.mapped('start_datetime')
            if start_datetime_list:
                last_meeting = max(start_datetime_list)
                sprint_length = self.sprint_id.sprint_length_days
                last_start_time = fields.Datetime.from_string(last_meeting)
                new_start_datetime = (last_start_time + timedelta(days=sprint_length))
                return fields.Datetime.to_string(new_start_datetime)
            else:
                return datetime.now()
        else:
            return datetime.now()

    @api.multi  # Getting the Start DateTime Daily Meeting
    def _compute_start_time_daily_hrs(self):
        self.ensure_one()  # One record expected, raise error if self is an unexpected recordset
        meetings = self.search([('meeting_type', '=', 'daily'), ('project_id', '=', self.project_id.id)])
        for record in meetings:
            start_datetimes = meetings.mapped('start_datetime')
        last_meeting = max(start_datetimes)
        last_start_time = fields.Datetime.from_string(last_meeting).time()
        sprint_start_date = fields.Date.from_string(self.sprint_id.date_start)
        new_start_date = (sprint_start_date + timedelta(days=1))
        next_datetime_start = datetime.combine(new_start_date, last_start_time)
        return fields.Datetime.to_string(next_datetime_start)

    @api.multi  # Getting the Stop DateTime
    def _compute_stop_time_hrs(self, start, duration):
        self.ensure_one()  # One record expected, raise error if self is an unexpected recordset
        value = {}
        if not (start and duration) or self.allday is True:
            return value
        start_time = fields.Datetime.from_string(start)
        hour, minute = self._float_time_convert(duration)
        end_datetime = (start_time + timedelta(hours=hour, minutes=minute))
        end_datetime_str = fields.Datetime.to_string(end_datetime)
        return end_datetime_str

    # Getting the Start/Stop Dates and other items depending on Meeting-type
    @api.onchange('meeting_type', 'project_id', 'sprint_id')
    def _onchange_meeting_type(self):
        value = {}
        if not self.project_id and self.sprint_id:
            return value
        if self.meeting_type == "sprint":  # Sprint Calendar Items
            self.allday = True
            self.start_date = self.sprint_id.date_start
            self.stop_date = self.sprint_id.date_stop
            self.start_datetime = self.start_date
            self.stop_datetime = self.stop_date
            self.name = self.name = "%s - %s" % (self.sprint_id.name, self.start_date)
        elif self.meeting_type == "daily":  # Daily Scrum Items
            print "daily"
            self.allday = False
            self.start_datetime = self._compute_start_time_daily_hrs()
            self.start_date = self.start_datetime
            self.duration = 0.25
            self.sprint_dm_id = self.sprint_id
            self.name = self.name = "%s - %s" % ("First Daily", self.start_date)
            self.agenda = self._get_meeting_text(self.meeting_type, 'agenda')  # Get the default text from Color/Meeting Definition
            self.protocol = self._get_meeting_text(self.meeting_type, 'protocol')
            self.stop_datetime = self._compute_stop_time_hrs(self.start_datetime, self.duration)
        elif self.meeting_type == "planning":  # Sprint Planning Items
            self.allday = False
            self.start_datetime = self._compute_start_time_hrs(self.meeting_type)
            # self.write(VALUES)  TODO How to store the actual record?
            # self.write({'allday': False})
            self.duration = self.project_id.default_planning_hrs
            # test = self._get_id(self.meeting_type)
            self.sprint_dm_id = ""
            self.sprint_id.meeting_p_id = self.id  # TODO does not work?
            self.name = self.name = "%s - %s - %s" % ("Sprint Planning", self.sprint_id.name, self.start_datetime)
            self.agenda = self._get_meeting_text(self.meeting_type, 'agenda')  # Get the default text from Color/Meeting Definition
            self.protocol = self._get_meeting_text(self.meeting_type, 'protocol')
            self.stop_datetime = self._compute_stop_time_hrs(self.start_datetime, self.duration)
        elif self.meeting_type == "review":
            self.allday = False
            self.start_datetime = self._compute_start_time_hrs(self.meeting_type)
            self.duration = self.project_id.default_review_hrs
            self.sprint_dm_id = ""
            self.sprint_id.meeting_rev_id = self.id
            self.name = self.name = "%s - %s - %s" % ("Sprint Review", self.sprint_id.name, self.start_datetime)
            self.agenda = self._get_meeting_text(self.meeting_type, 'agenda')  # Get the default text from Color/Meeting Definition
            self.protocol = self._get_meeting_text(self.meeting_type, 'protocol')
            self.stop_datetime = self._compute_stop_time_hrs(self.start_datetime, self.duration)
        elif self.meeting_type == "retro":
            self.allday = False
            self.start_datetime = self._compute_start_time_hrs(self.meeting_type)
            self.sprint_dm_id = ""            
            self.sprint_id.meeting_retro_id = self.id
            self.duration = self.project_id.default_review_hrs / 2
            self.name = self.name = "%s - %s - %s" % ("Retrospective", self.sprint_id.name, self.start_datetime)
            self.agenda = self._get_meeting_text(self.meeting_type, 'agenda')  # Get the default text from Color/Meeting Definition
            self.protocol = self._get_meeting_text(self.meeting_type, 'protocol')
            self.stop_datetime = self._compute_stop_time_hrs(self.start_datetime, self.duration)
        elif self.meeting_type == "other":
            self.allday = False
            self.start_datetime = datetime.now()
            self.duration = 1.0
            self.sprint_dm_id = ""
            self.start_date = self.start_datetime
            self.stop_date = self.stop_datetime
            self.name = self.name = "Other Meeting"
            self.agenda = self._get_meeting_text(self.meeting_type, 'agenda')  # Get the default text from Color/Meeting Definition
            self.protocol = self._get_meeting_text(self.meeting_type, 'protocol')

    @api.multi  # getting integer out of float from widget "float_time"
    def _float_time_convert(self, float_val):
        factor = float_val < 0 and -1 or 1
        val = abs(float_val)
        return (factor * int(math.floor(val)), int(round((val % 1) * 60)))
    """
    @api.multi
    def _get_id(self, meeting_type):  # TODO get the current ID
        self.ensure_one()  # One record expected, raise error if self is an unexpected recordset
        sprint_meeting_id1 = {}
        sprint_meeting_id2 = {}
        sprint_meeting = {}
        for sprint in self.sprint_id.meeting_ids:
            if sprint.id > 0:
                sprint_meeting_id1 = sprint.id
                print "data Sprint", sprint_meeting_id1
            for record in self.search([('meeting_type', '=', meeting_type)]):  # ('sprint_id', '=', sprint_meeting_ids)
                sprint_meeting_id2 = record.id  # .search([('sprint_id', '=', sprint_meeting_id1)])
                print "data from get_id2", sprint_meeting_id1, sprint_meeting_id2, meeting_type
            if sprint_meeting_id1 == sprint_meeting_id2:
                sprint_meeting = sprint_meeting_id2
            else:
                pass
        print "data from result", sprint_meeting_id1, sprint_meeting
        return sprint_meeting
    """
    @api.multi  # Getting the default text from Color/Meeting Definition
    def _get_meeting_text(self, meeting_type, text_type):
        self.ensure_one()  # One record expected, raise error if self is an unexpected recordset
        project_id = self.project_id.id
        definition = self.env['project.scrum.color_def'].search([('project_ids', '=', project_id),
                                                                 ('def_type', '=', "meeting"),
                                                                 ('meeting_type', '=', meeting_type)])
        if text_type == "agenda":
            text_str = str(definition.mapped('agenda'))
            text_test = re.findall('\n', text_str, re.DOTALL)
            text_cleaned1 = re.sub('\n', '', text_str)  # TODO does not match \n new line char
            text_cleaned = re.sub(' +', ' ', text_cleaned1)
            return text_cleaned
        if text_type == "protocol":
            text_str = str(definition.mapped('protocol'))
            text_cleaned1 = re.sub(r'\n', '', text_str)
            text_cleaned = re.sub(' +', ' ', text_cleaned1)
            return str(text_cleaned)
        else:
            return str("No default text defined yet!")

    @api.multi  # create all daily_meetings for one sprint
    def _create_daily_meetings(self, start_date, sprint_length):
        # Start with today.
        start = fields.Date.from_string(start_date)
        # Add 1 to x days and get future dates and time.
        for add in range(1, sprint_length - 1):
            next_date = start + timedelta(days=add)
            next_str = fields.Date.to_string(next_date)
            actual_time_start = fields.Datetime.from_string(self.start_datetime).time()
            actual_time_stop = fields.Datetime.from_string(self.stop_datetime).time()
            next_datetime_start = datetime.combine(next_date, actual_time_start)
            next_datetime_stop = datetime.combine(next_date, actual_time_stop)
            self.create({'allday': False,
                         'meeting_type': self.meeting_type,
                         'project_id': self.project_id.id,
                         'sprint_id': self.sprint_id.id,
                         'start_date': next_str,
                         'duration': self.duration,
                         'start_datetime': next_datetime_start,
                         'stop_datetime': next_datetime_stop,
                         'sprint_dm_id': self.sprint_id.id,
                         'state': "sent",
                         'name': "%s - Daily - %s" % (self.sprint_id.name, next_str)
                         })

    @api.multi
    def send_email(self):
        """ Open a window to compose an email, with one of meeting template
            messages loaded by default
        """
        assert len(self) == 1, 'This option should only be used for a single id at a time.'
        if self.meeting_type == "daily":  # Daily Scrum Items
            if self.sprint_id.sprint_length_days:
                self.start_date = self.start_datetime
                template = self.env.ref('project_scrum.email_template_scrum_meeting_daily', False)
                dummy = self._create_daily_meetings(self.start_date, self.sprint_id.sprint_length_days)
            else:
                raise Exception("The sprint length of your sprint is not set.")
        else:
            template = self.env.ref('project_scrum.email_template_scrum_meeting', False)
        compose_form = self.env.ref('mail.email_compose_message_wizard_form', False)
        self.state = 'sent'
        ctx = dict(
            default_model='project.scrum.meeting',
            default_res_id=self.id,
            default_use_template=bool(template),
            default_template_id=template.id,
            default_composition_mode='comment',
        )
        return {
            'name': ('Compose Email'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form.id, 'form')],
            'view_id': compose_form.id,
            'target': 'new',
            'context': ctx,
        }

    @api.multi  # TODO get the followers of the active Scrum Project
    def get_partner_ids(self, follower_ids):
        # self.ensure_one()
        followers = self.sudo().env['mail.followers'].search([('res_id', '=', follower_ids.ids)])
        partners = followers.mapped('partner_id')

        # for record in self.env['mail.followers']:
         # search([('record.res_id', '=', follower_ids.ids)]):
         # print "FOLLOWER records: ", fields(record.partner_id)
            # partners2 = self.env['mail_followers'].mapped('partner_id')
            # print "FOLLOWER ids: ", follower_ids.ids, record
        # print "FOLLOWER ids: ", follower_ids.ids, followers1, followers, partners
        # result = str([self.env.mail_followers.partner_id.id for follower in follower_ids]).replace('[', '').replace(']', '')
        return ""


class DefOfDone(models.Model):
    _name = 'project.scrum.def_done'
    _description = 'Project Scrum Def of Done'
    _order = 'sequence'

    @api.model
    def _read_group_stage_ids(self, present_ids, domain, **kwargs):
        # project_id = self._resolve_project_id_from_context()
        result = self.env['project.scrum.def_done.state'].search([]).name_get()
        return result, None

    _group_by_full = {
        'state_def': _read_group_stage_ids,
        }

    name = fields.Char(string='Def Name', required=True, size=60)
    color = fields.Integer('Color Index')
    parent_id = fields.Many2one("project.scrum.def_done", oldname="definition_id", string="Parent Definition", required=False)
    child_definition_ids = fields.One2many("project.scrum.def_done", "parent_id",
                                           string="Child Definitions", required=False)
    project_ids = fields.Many2many(comodel_name='project.project', string='Projects')
    sprint_ids = fields.Many2many(comodel_name='project.scrum.sprint', string='Used in Sprints')
    user_story_id = fields.Many2one(comodel_name="project.scrum.us", string="User Story")
    description = fields.Html(string='Description', track_visibility='onchange')
    description_short = fields.Text(compute='_conv_html2text', store=True)
    sequence = fields.Integer(string='Sequence', select=True)
    state_def = fields.Many2one(comodel_name='project.scrum.def_done.state', string='Stage',
                                track_visibility='onchange', select=True, copy=False)
    stage = fields.Integer(compute='_get_stage', store=True)
    partner_ids = fields.Many2many(comodel_name='res.partner', string='Stakeholders',
                                   help="Which partners shares interest and influences this Definition?")
    company_id = fields.Many2one(related='project_ids.analytic_account_id.company_id')

    @api.one
    @api.depends('description')
    def _conv_html2text(self):  # method that return a short text from description of Definitions
        self.description_short = re.sub('<.*?>', ' ', self.description)
        if len(self.description_short)>= 150:
            self.description_short = self.description_short[:149]

    @api.one
    @api.depends('state_def')
    def _get_stage(self):
        self.stage = self.state_def
        return True


class DefOfDoneState(models.Model):

    _name = 'project.scrum.def_done.state'
    _description = 'Project Scrum Def of Done Stages'
    _order = 'sequence'

    name = fields.Char(string='Name', size=60, required=True)
    description = fields.Text(string='Description')
    sequence = fields.Integer(string='Sequence', select=True)
    fold = fields.Boolean('Folded in Tasks Pipeline',
                          help='This stage is folded in the kanban view when '
                          'there are no records in that stage to display.')


class ColorDefinition(models.Model):

    _name = 'project.scrum.color_def'
    _description = 'Project Scrum Color-Text Definitions'
    _order = 'def_type,sequence'

    name = fields.Char(string='Name', required=True, size=60,
                       help="Color Definitions or Codes are only to inform about the use of colors in tasks. "
                       "The Meetings texts are used as defaults for the different meetings types!")
    color = fields.Integer(string='Color Index')
    color_txt = fields.Char(string='Color Text', size=20)
    sequence = fields.Integer(string='Sequence', select=True)
    def_type = fields.Selection([
                ('color', 'Color Definitions'),
                ('meeting', 'Meeting Texts'),
                ],
                string='Definition Type', required=True, default='color',
                       help="This model is used for both Color Definition and Default Meetings texts")
    meeting_type = fields.Selection([
        ('daily', 'Daily Scrum'),
        ('planning', 'Sprint Planning'),
        ('review', 'Sprint Review'),
        ('retro', 'Sprint Retrospective'),
        ('sprint', 'Sprint'),
        ('other', 'Other Meetings')
        ],
        string='Meeting Type', required=False,
        help="The Meetings texts are used as defaults for the different meetings types!")
    project_ids = fields.Many2many(comodel_name="project.project", string="Used in Projects")
    tag_ids = fields.Many2many('project.tags', string='Tags')
    description = fields.Text(string='Description')
    agenda = fields.Html(string='Meeting Agenda', required=False,
                         help="Default Agenda text for meetings")
    protocol = fields.Html(string='Meeting Outcome', required=False,
                           help="Default Protocol text for meetings")

    # TODO does not work, still possible to create more then one record per meeting_type
    # project_ids is not present in DB!
    _sql_constraints = [
            ('meeting_def_unique',
             'UNIQUE (def_type, meeting_type, project_ids)',
             'Only one default meeting item is allowed per Project!')]