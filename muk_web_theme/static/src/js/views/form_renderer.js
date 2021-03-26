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

odoo.define('muk_web_theme.FormRenderer', function (require) {
"use strict";

const core = require('web.core');
const config = require("web.config");

const FormRenderer = require('web.FormRenderer');

FormRenderer.include({
    _renderHeaderButtons() {
        const $buttons = this._super(...arguments);
        if (
            !config.device.isMobile ||
            !$buttons.is(":has(>:not(.o_invisible_modifier))")
        ) {
            return $buttons;
        }

        $buttons.addClass("dropdown-menu");
        const $dropdown = $(
            core.qweb.render("muk_web_theme.MenuStatusbarButtons")
        );
        $buttons.addClass("dropdown-menu").appendTo($dropdown);
        return $dropdown;
    },
});

});