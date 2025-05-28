/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

const commandRegistry = registry.category("discuss.channel_commands");

commandRegistry
    .add("clear", {
        channel_types: ["channel", "chat"],
        help: _t("Clear chat with AI Bot"),
        methodName: "execute_command_clear_ai_chat",
    });
