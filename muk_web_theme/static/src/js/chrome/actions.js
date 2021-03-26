/**********************************************************************************
*
*    Copyright (c) 2017-today MuK IT GmbH.
*
*    This file is part of MuK Grid Snippets
*    (see https://mukit.at).
*
*    This program is free software: you can redistribute it and/or modify
*    it under the terms of the GNU Lesser General Public License as published by
*    the Free Software Foundation, either version 3 of the License, or
*    (at your option) any later version.
*
*    This program is distributed in the hope that it will be useful,
*    but WITHOUT ANY WARRANTY; without even the implied warranty of
*    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
*    GNU Lesser General Public License for more details.
*
*    You should have received a copy of the GNU Lesser General Public License
*    along with this program. If not, see <http://www.gnu.org/licenses/>.
*
**********************************************************************************/

odoo.define('muk_web_theme.ActionManager', function (require) {
"use strict";

const ActionManager = require('web.ActionManager');

ActionManager.include({
    _handleAction(action) {
        return this._super(...arguments).then($.proxy(this, '_hideMenusByAction', action));
    },
    _hideMenusByAction(action) {
        const unique_selection = '[data-action-id=' + action.id + ']';
        $(_.str.sprintf('.o_menu_apps .dropdown:has(.dropdown-menu.show:has(%s)) > a', unique_selection)).dropdown('toggle');
        $(_.str.sprintf('.o_menu_sections.show:has(%s)', unique_selection)).collapse('hide');
    },
});

});
