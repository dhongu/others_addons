# -*- coding: utf-8 -*-
# © <2016> <CoÐoo Project, Lucas Huber; Vertel AB>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

{
    'name': 'Project Scrum',
    'version': '9.0.1.9.x',
    'category': 'Project Management',
    'summary': 'SCRUM framework integrated into Odoo Project',
    'description': """
Using Scrum to plan the work in a team.
=========================================================================================================
More information:
    """,

    'author': 'CoÐoo Project, Lucas Huber, '
              'Vertel AB'
              ,
    'website': 'https://github.com/codoo/project-scrum',
    'external_dependencies': {
        'python': [],
        'bin': [],
    },
    'depends': ['project',
                'mail',
                'project_issue',
                'hr_timesheet'
                ],
    'data': [
        'security/ir.model.access.csv',
        'security/project_security.xml',
        'views/project_scrum_view.xml',
        'views/project_scrum_sprint_view.xml',
        'views/project_scrum_project_view.xml',
        'views/project_dashboard.xml',
        'views/project_scrum_menu_view.xml',
        'data/project_scrum_data_base.xml',
        'data/project_scrum_data_def_o_done.xml',
        'data/project_scrum_data_color_def.xml',
        'data/project_scrum_data_meetings.xml',
       ],

    'installable': True,
    'auto_install': False,
    'application': True,
}


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
