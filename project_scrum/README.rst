.. image:: https://img.shields.io/badge/licence-LGPL--3-blue.svg
   :target: http://www.gnu.org/licenses/lgpl-3.0-standalone.html
   :alt: License: LGPL-3

=============
Project Scrum
=============

This module extends the functionality of Project to run projects as Scrum projects.
Is supports User Stories, Sprints, Tasks incl. Backlog and Impediments as Issues.
It allows to manage the relevant Scrum Meetings as Daily, Scrum planning, review and retrospective.

It is a complete revamped version of the Scrum app from Vertel AB https://github.com/vertelab/odoo-project_scrum.

THIS IS A BETA VERSION! You can use it at your own risk!

Dependencies
============

* project
* project_issue
* project_timesheet

Installation
============

To install this module, you need to:

#. clone the branch 9.0 of the repository https://github.com/codoo/project-scrum.git
#. copy this repository into your configuration addons-path
#. update the module list (need to be Developer mode)
#. search for "scrum" in your addons
#. install the module
#. to improve the start process a default Scrum project with one sprint is installed by default

Configuration
=============

To configure this module, you need to:

#. Enable "Manage time estimation on tasks" in the user settings!
#. Give all the team members minimum User Rights for the Project Module Settings->Users->Application
#. Give to the Scrum Master and or the Product Owner Administration -> Configuration and Project -> Manager permission
#. Manage the Stages in Configuration/Stages according your needs. Attention at least one stage has to be assigned to each Scrum Stage. Don't forget to assign each stage to any new project!
#. Manage the Definitions of Done according your needs (some definitions are installed by default)

Usage
=====

To use this module, you need to:

#. Change the Color/Meetings Definitions according your needs
#. Change the Meeting texts in Color/Meetings Definitions according your needs
#. We recommend to use this module with the project_team module.
https://github.com/JayVora-SerpentCS/SerpentCS_Contributions-v8/tree/9.0/project_team


Known issues / Roadmap
======================

* There are still several issues.
* Coping of default meetings html text is not fixing the /n (newline) characters.
* While creating a new planning/review/retro meeting the meeting does not link automatically to the sprint fields.
* You are welcome to help improve this app.

