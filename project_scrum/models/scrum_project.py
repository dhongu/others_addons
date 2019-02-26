# -*- coding: utf-8 -*-
# © <2016> <CoÐoo Project, Lucas Huber, Vertel AB>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).
from odoo import models, fields, api
# import openerp.tools
# import re
# import time
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta
import logging
_logger = logging.getLogger(__name__)


class ProjectProjectScrum(models.Model):
    _inherit = 'project.project'

    # def _auto_init(self, cr, context=None):
        #self._group_by_full['sprint_id'] = _read_group_sprint_id
        #self._group_by_full['us_id'] = _read_group_us_id
        #super(project_task, self)._auto_init(cr, context)

    @api.model
    def _read_group_stage_ids(self, stages, domain, order):
        stage_ids = stages._search([], order=order, access_rights_uid=SUPERUSER_ID)
        return stages.browse(stage_ids)


    # def _read_group_stage_ids_old(self, cr, uid, ids, domain, read_group_order=None, access_rights_uid=None, context=None):
    #     stage_obj = self.pool.get('project.task.type')
    #     order = stage_obj._order
    #     access_rights_uid = access_rights_uid or uid
    #     if read_group_order == 'stage_id desc':
    #         order = '%s desc' % order
    #     search_domain = []
    #     project_id = self._resolve_project_id_from_context(cr, uid, context=context)
    #     if project_id:
    #         search_domain += ['|', ('project_ids', '=', project_id)]
    #     search_domain += [('id', 'in', ids)]
    #     stage_ids = stage_obj._search(cr, uid, search_domain, order=order, access_rights_uid=access_rights_uid, context=context)
    #     result = stage_obj.name_get(cr, access_rights_uid, stage_ids, context=context)
    #     # restore order of the search
    #     result.sort(lambda x,y: cmp(stage_ids.index(x[0]), stage_ids.index(y[0])))
    #
    #     fold = {}
    #     for stage in stage_obj.browse(cr, access_rights_uid, stage_ids, context=context):
    #         fold[stage.id] = stage.fold or False
    #     return result, fold

    scrum_master_id = fields.Many2one('res.users', 'Scrum Master', select=True, track_visibility='onchange')
    project_code = fields.Char(string="Project Code", size=6, index=True,
                               help="Short code to identify the Project. Used for Sprint name!")
    description = fields.Html(string="Description", default="""
                                    Say a few words about this project""")
    sprint_ids = fields.One2many(comodel_name="project.scrum.sprint", inverse_name="project_id", string="Sprints")
    user_story_ids = fields.One2many(comodel_name="project.scrum.us", inverse_name="project_id", string="User Stories")
    meeting_ids = fields.One2many(comodel_name="project.scrum.meeting", inverse_name="project_id", string="Meetings")
    def_o_done_ids = fields.Many2many(comodel_name="project.scrum.def_done", inverse_name="project_ids",
                                      string="Def. of Done")
    color_def_ids = fields.Many2many(comodel_name="project.scrum.color_def", inverse_name="project_ids", string="Color Definitions",
                                     help="Color Definitions are only to inform about using colors in tasks. "
                                          "No function behind!")
    sprint_count = fields.Integer(compute='_sprint_count', string="Sprints")
    user_story_count = fields.Integer(compute='_user_story_count', string="User Stories")
    meeting_count = fields.Integer(compute='_meeting_count', string="Meetings")
    def_o_done_count = fields.Integer(compute='_def_o_done_count', string="Def of Done")
    use_scrum = fields.Boolean(string="Using Scrums", store=True)
    default_sprintlength = fields.Integer(string='Default sprint length', required=False, default=14,
                                          help="Default Sprint time for this project, in days")
    team_members = fields.Integer(string='Nr. of team members', required=False, default=6,
                                  help="How many team members are in the team")
    manhours = fields.Integer(string='Man Hours', required=False,
                              help="How many hours you expect this project needs before it's finished")
    default_hrs = fields.Float(string='Default daily hours', required=True, default=6.0714,
                               help="How many hours an average team member ist working per day on the project."
                                    "(Including weekend! 7 days!)")
    default_planning_hrs = fields.Float(string='Default Sprint Planning hours', required=True, default=6.0,
                                        help="How many hours the Sprint Planning Meetings should take?")
    default_review_hrs = fields.Float(string='Default Sprint Review hours', required=True, default=4.0,
                                      help="How many hours the Sprint Reviews should take?")
    default_story_color = fields.Many2one(comodel_name="project.scrum.color_def", string='Default User Story color',
                                          default="", help="Choose color from Color Definition")
    meeting_agenda = fields.Html(related='meeting_ids.agenda')
    """
    @api.one # TODO
    @api.constrains('project_code')
    def _check_name_size(self):
        if len(self.name) < 5:
            raise ValidationError('Must have max. 5 chars!')
    """
    def _sprint_count(self):    # method that calculate how many sprints exist
        for p in self:
            p.sprint_count = len(p.sprint_ids)

    def _user_story_count(self):    # method that calculate how many user stories exist
        for p in self:
            p.user_story_count = len(p.user_story_ids)

    def _meeting_count(self):    # method that calculate how many meetings exist
        for p in self:
            p.meeting_count = len(p.meeting_ids)

    def _def_o_done_count(self):    # method that calculate how many Def of Done exist
        for p in self:
            p.def_o_done_count = len(p.def_o_done_ids)


class ResPartner(models.Model):
    """
    Add some field in partner
    """
    _inherit = 'res.partner'

    stakeholder_us_ids = fields.Many2many(comodel_name='project.scrum.us', string='User Story Stakeholders')
    stakeholder_dod_ids = fields.Many2many(comodel_name='project.scrum.def_done', string='Def. Stakeholders')


class ProjectTasks(models.Model):
    """
    Add some field in Task model
    """
    _inherit = "project.task"
    _order = "sequence"

#    user_id = fields.Many2one('res.users', 'Assigned to', select=True, track_visibility='onchange', default="")
#    actor_ids = fields.Many2many(comodel_name='project.scrum.actors', string='Actor')
    sprint_id = fields.Many2one(comodel_name='project.scrum.sprint', string='Sprint')
    task_us_ids = fields.Many2one(comodel_name='project.scrum.us', string='User Stories')
    estimated_hrs = fields.Float(string="Estimated hours", required=False, default=4,
                                 help="Hours estimation of Team using Scrum Poker")
    spent_hrs = fields.Float(compute='_compute_spent_hrs', string="Spent hours",
                             help="Hours already spent on this task (sum of timesheets)")
    use_scrum = fields.Boolean(related='project_id.use_scrum')
    repo_url = fields.Char('Repo URL')
    description = fields.Html('Description')

    @api.one
    def _compute_spent_hrs(self):
        self.spent_hrs = self.effective_hours
        return True

    @api.model  # get sprint id
    def _read_group_sprint_id(self, present_ids, domain, **kwargs):
        project = self.env['project.project'].browse(self._resolve_project_id_from_context())

        if project.use_scrum:
            sprints = self.env['project.scrum.sprint'].search([('project_id', '=', project.id)], order='sequence').name_get()
            return sprints, None
        else:
            return [], None

    @api.model
    def _read_group_us_id(self, present_ids, domain, **kwargs):
        project = self.env['project.project'].browse(self._resolve_project_id_from_context())

        if project.use_scrum:
            user_stories = self.env['project.scrum.us'].search([('project_id', '=', project.id)], order='sequence').name_get()
            return user_stories, None
        else:
            return [], None


class ProjectTasksType(models.Model):
    _inherit = "project.task.type"

    scrum_stages = fields.Selection([
        ('draft', 'Draft'),
        ('pbacklog', 'Product Backlog'),
        ('sbacklog', 'Sprint Backlog'),
        ('progress', 'In progress'),
        ('done', 'Done')
    ], string='Scrum Stages', help='Stages to define SCRUM process. At least one stage per Scrum Stage is required.')


class ProjectIssue(models.Model):
    _inherit = 'project.issue'

    sprint_id = fields.Many2one(comodel_name='project.scrum.sprint', string='Sprint')
    scrum_meeting_ids = fields.Many2many(comodel_name='project.scrum.meeting', string='Scrum Meetings')
