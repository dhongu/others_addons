/** @odoo-module */
import {FormController} from "@web/views/form/form_controller";
import {patch} from "@web/core/utils/patch";
import {useSetupView} from "@web/views/view_hook";

import {ConfirmationDialog} from "@web/core/confirmation_dialog/confirmation_dialog";
import {_t} from "@web/core/l10n/translation";
import { useOwnedDialogs, useService } from "@web/core/utils/hooks";

patch(FormController.prototype, {
    /* Patch FormController to restrict auto save in form views */
    setup() {
        super.setup(...arguments);
              this.action = useService("action");
        this.dialog = useService("dialog");
    },

    async create() {
        var isDirty =  await this.model.root.isDirty();
        if (isDirty) {
            return this.confirmDiscard();
        }
        await super.create(...arguments);
    },

    async confirmDiscard() {
        var self = this;
        const proceed = await new Promise((resolve) =>
            {
                this.model.dialog.add(ConfirmationDialog, {
                    title: _t("Confirm"),
                    body: _t("If you discard the current edits, all unsaved changes will be lost. You can cancel to return to edit mode."),
                    confirmLabel: _t("Discard"),
                    confirm: async () => {
                        self.model.root.discard();
                        resolve(true);
                    },
                    cancel: () => {
                        resolve(false);
                    },
                });
            });
            return proceed;
    },

    async beforeLeave() {
        var isDirty =  await this.model.root.isDirty();
        if (isDirty) {
            return this.confirmDiscard();
        }
        else {
            return super.beforeLeave();
        }

    }
});
