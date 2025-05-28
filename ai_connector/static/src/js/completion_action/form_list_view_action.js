/** @odoo-module */
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { ActionMenus, ACTIONS_GROUP_NUMBER } from "@web/search/action_menus/action_menus";
import { useService } from "@web/core/utils/hooks";
import { Component } from "@odoo/owl";


export class RunCompletion extends Component {
    static template = "ai_connector.RunCompletion";
    static props = ["title", "completion_id"];

    static components = { DropdownItem };

    setup() {
        this.action = useService("action");
        this.orm = useService("orm");
    }

    async runCompletion() {
        await this.orm.call("ai.completion", "run_completion",
            [this.props.completion_id, this.props.getActiveIds()]);

        this.action.doAction({
            type: "ir.actions.client",
            tag: "soft_reload"
        });
    }
}

patch(ActionMenus.prototype, {

    async getActionItems(props) {

        const items = await super.getActionItems(props);
        if ('registryItems' in props) {
            return items;
        }
        if (!('getActiveIds' in props)) {
            return items;
        }

        const results = await this.orm.call("ai.completion", "get_model_completions", [this.props.resModel]);
        results.forEach( res => {
            items.push({
                Component: RunCompletion,
                groupNumber: ACTIONS_GROUP_NUMBER,
                key: res['id'],
                props: {
                    ...this.props,
                    'title': _t(res['name']),
                    'completion_id': res['id'],
                },
            });
        });
        return items;

    },

})
