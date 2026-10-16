import {registry} from "@web/core/registry";

registry.category("web_tour.tours").add("website_sale_filter_product_brand", {
    url: "/shop",
    steps: () => [
        {
            content: "Check brand",
            trigger: 'input[name="brand"]',
            run: "click",
        },
        {
            content: "Brand should be checked after the shop reload",
            // the `checked` attribute is only set by the server rendering
            trigger: 'input[name="brand"][checked]',
        },
    ],
});
