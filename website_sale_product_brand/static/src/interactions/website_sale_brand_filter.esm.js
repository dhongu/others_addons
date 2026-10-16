import {ShopPage} from "@website_sale/interactions/shop_page";
import {patch} from "@web/core/utils/patch";
import {redirect} from "@web/core/utils/urls";
import {rpc} from "@web/core/network/rpc";

patch(ShopPage.prototype, {
    start() {
        super.start(...arguments);
        this.setupBrandFilter();
    },

    setupBrandFilter() {
        this.brandFilterForm = this.el.querySelector("form[data-brand-filter-mode]");
        if (!this.brandFilterForm) {
            return;
        }
        // The core change handler is bound to the inputs present at start: the
        // brands loaded later ("Show more", letters) are handled here.
        const initialInputs = new Set(this.brandFilterForm.querySelectorAll("input"));
        this.addListener(this.brandFilterForm, "change", (ev) => {
            if (ev.target.matches("input[name='brand']") && !initialInputs.has(ev.target)) {
                return this.onChangeAttribute({currentTarget: ev.target});
            }
        });
        const loadMoreButton = this.brandFilterForm.querySelector(
            ".o_wsale_brand_load_more"
        );
        if (loadMoreButton) {
            this.addListener(loadMoreButton, "click", this.loadMoreBrands);
        }
        for (const letter of this.brandFilterForm.querySelectorAll("[data-letter]")) {
            this.addListener(letter, "shown.bs.collapse", this.loadBrandLetter);
        }
        for (const openedLetter of this.brandFilterForm.querySelectorAll(
            "[data-letter].show"
        )) {
            this.loadBrandLetter({currentTarget: openedLetter});
        }
    },

    getBrandRpcParams(extraParams = {}) {
        const url = new URL(window.location.href);
        const attributeValues = {};
        for (const [key, value] of url.searchParams.entries()) {
            if (!["brand", "brand_ids", "search", "order", "page"].includes(key)) {
                attributeValues[key] = value;
            }
        }
        return {
            search: this.brandFilterForm.dataset.search || "",
            category_id: this.brandFilterForm.dataset.categoryId || false,
            attribute_values: attributeValues,
            brand_ids: [
                ...url.searchParams.getAll("brand"),
                ...url.searchParams.getAll("brand_ids"),
            ],
            ...extraParams,
        };
    },

    async loadMoreBrands(ev) {
        const button = ev.currentTarget;
        button.disabled = true;
        const result = await this.waitFor(
            rpc(
                "/shop/brand_filter/load_more",
                this.getBrandRpcParams({
                    offset: parseInt(button.dataset.offset || "0", 10),
                    limit: parseInt(this.brandFilterForm.dataset.brandLimit || "5", 10),
                    exclude_brand_ids: (button.dataset.excludeBrandIds || "")
                        .split(",")
                        .filter(Boolean),
                })
            )
        );
        this.brandFilterForm
            .querySelector("[data-brand-filter-items]")
            .insertAdjacentHTML("beforeend", result.html);
        if (result.has_more) {
            button.dataset.offset = result.next_offset;
            button.disabled = false;
        } else {
            button.remove();
        }
    },

    async loadBrandLetter(ev) {
        const panel = ev.currentTarget;
        if (panel.dataset.loaded === "1") {
            return;
        }
        const button = panel.querySelector(".o_wsale_brand_letter_load_more");
        const result = await this.waitFor(
            rpc(
                "/shop/brand_filter/load_letter",
                this.getBrandRpcParams({
                    letter: panel.dataset.letter,
                    offset: 0,
                    limit: parseInt(
                        this.brandFilterForm.dataset.brandLetterLimit || "50",
                        10
                    ),
                })
            )
        );
        panel.querySelector("[data-brand-filter-items]").innerHTML = result.html;
        panel.dataset.loaded = "1";
        if (button && result.has_more) {
            button.dataset.offset = result.next_offset;
            button.classList.remove("d-none");
            this.addListener(button, "click", (clickEv) =>
                this.loadMoreBrandLetter(clickEv, panel)
            );
        }
    },

    async loadMoreBrandLetter(ev, panel) {
        const button = ev.currentTarget;
        button.disabled = true;
        const result = await this.waitFor(
            rpc(
                "/shop/brand_filter/load_letter",
                this.getBrandRpcParams({
                    letter: panel.dataset.letter,
                    offset: parseInt(button.dataset.offset || "0", 10),
                    limit: parseInt(
                        this.brandFilterForm.dataset.brandLetterLimit || "50",
                        10
                    ),
                })
            )
        );
        panel
            .querySelector("[data-brand-filter-items]")
            .insertAdjacentHTML("beforeend", result.html);
        if (result.has_more) {
            button.dataset.offset = result.next_offset;
            button.disabled = false;
        } else {
            button.remove();
        }
    },

    /**
     * On a brand landing page, changing the brands leaves the landing page
     * (its header is not part of the AJAX shop reload): full page load of the
     * filtered shop.
     *
     * @override
     */
    async onChangeAttribute(ev) {
        const form = ev.currentTarget.closest("form");
        if (
            form?.matches("[data-brand-filter-mode]") &&
            this.el.querySelector("#brand_landing_header")
        ) {
            const url = new URL(form.action);
            redirect(`${url.pathname}?${this._getSearchParams(form).toString()}`);
            return;
        }
        return super.onChangeAttribute(...arguments);
    },

    /**
     * The brand checkboxes live in their own `form.js_attributes`: the core
     * handler only reads the inputs of the changed form, so for the brand form
     * we keep the other filters from its action (`keep(brand=0)`) and add the
     * checked brands as a single comma separated `brand` param (the shop
     * reload RPC receives the search params as an object).
     *
     * @override
     */
    _getSearchParams(form) {
        if (!form.matches("[data-brand-filter-mode]")) {
            return super._getSearchParams(...arguments);
        }
        const searchParams = new URL(form.action).searchParams;
        searchParams.delete("brand");
        searchParams.delete("brand_ids");
        searchParams.delete("page");
        const brandIds = [
            ...new Set(
                Array.from(form.querySelectorAll("input[name='brand']:checked"))
                    .map((input) => input.value)
                    .filter(Boolean)
            ),
        ];
        if (brandIds.length) {
            searchParams.set("brand", brandIds.join(","));
        }
        return searchParams;
    },
});
