# © 2016 Serpent Consulting Services Pvt. Ltd. (http://www.serpentcs.com)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from urllib.parse import urlencode, urlsplit

from odoo.fields import Domain
from odoo.http import request, route

from odoo.addons.website.controllers.main import QueryURL
from odoo.addons.website.models.ir_http import sitemap_qs2dom
from odoo.addons.website_sale.const import SHOP_PATH
from odoo.addons.website_sale.controllers.main import (
    WebsiteSale as WebsiteSaleBase,
)


class WebsiteSale(WebsiteSaleBase):
    BRAND_LIMIT = 5
    BRAND_LETTER_LIMIT = 50

    def _as_int_list(self, values):
        """Return the brand ids found in ``values``.

        Values can be ids, digit strings or comma separated digit strings
        (``brand=1,2``: the shop filters are sent as a single query param on
        Odoo 20, like the tags)."""
        if values is None or isinstance(values, (int, str)):
            values = [values]
        ids = []
        for value in values:
            for part in str(value or "").split(","):
                part = part.strip()
                if part.isdigit() and int(part) not in ids:
                    ids.append(int(part))
        return ids

    def _get_brand_from_query(self, query_args, fallback_brand=None):
        brand_value = (
            query_args.get("brand") or query_args.get("brand_ids") or fallback_brand
        )
        brand_ids = self._as_int_list(brand_value)
        if not brand_ids:
            return request.env["product.brand"]
        return request.env["product.brand"].browse(brand_ids[0])

    def _get_brand_from_slug(self, brand_slug):
        brand_id = request.env["ir.http"]._unslug(brand_slug)[1]
        return request.env["product.brand"].browse(brand_id)

    def _get_current_brand(self):
        return getattr(request, "_website_sale_brand", request.env["product.brand"])

    def _set_current_brand(self, brand):
        request._website_sale_brand = brand

    def _clear_current_brand(self):
        if hasattr(request, "_website_sale_brand"):
            delattr(request, "_website_sale_brand")

    def _brand_visible_on_website(self, brand):
        brand = brand.sudo().exists()
        if not (brand and brand.is_published):
            return False
        return brand.website_id.id in (False, request.env.website.id)

    def sitemap_brands(env, rule, qs):  # noqa: N805
        website = env.website
        if website and website.ecommerce_access == "logged_in" and not qs:
            return

        product_brand_model = env["product.brand"]
        domain = sitemap_qs2dom(qs, f"{SHOP_PATH}/brand", product_brand_model._rec_name)
        domain &= product_brand_model._website_public_domain(website=website)
        for brand in product_brand_model.search(domain):
            loc = f"{SHOP_PATH}/brand/{env['ir.http']._slug(brand)}"
            if not qs or qs.lower() in loc:
                yield {"loc": loc}

    def _update_domain(self, brands_list, domain):
        selected_brand_ids = self._as_int_list(brands_list)
        if not selected_brand_ids:
            return domain
        domain_no_brand = [
            leaf
            for leaf in domain
            if not (
                isinstance(leaf, (list, tuple))
                and leaf
                and leaf[0] == "product_brand_id"
            )
        ]
        return domain_no_brand + [("product_brand_id", "in", selected_brand_ids)]

    def _get_brand_ids(self, req):
        if not hasattr(req, "getlist"):
            return []
        raw_brand_ids = req.getlist("brand") or req.getlist("brand_ids") or []
        return self._as_int_list(raw_brand_ids)

    def _build_brands_list(
        self,
        selected_brand_ids,
        search=None,
        products=None,
        search_products=None,
        category=None,
    ):
        brand_model = request.env["product.brand"].sudo()
        domain = brand_model._website_public_domain()
        if not products:
            domain = Domain.AND(
                [domain, [("id", "in", self._as_int_list(selected_brand_ids))]]
            )
        elif search or category:
            domain = Domain.AND([domain, [("product_ids", "in", search_products.ids)]])
        return brand_model.search(domain).filtered(
            lambda x: x.published_products_count > 0
            or x.show_without_published_products
        )

    def _get_product_counts_by_brand_ids(self, domain):
        public_brand_ids = (
            request.env["product.brand"]
            .sudo()
            .search(request.env["product.brand"]._website_public_domain())
            .ids
        )
        domain = Domain.AND(
            [
                domain,
                [
                    ("product_brand_id", "!=", False),
                    ("product_brand_id", "in", public_brand_ids),
                ],
            ]
        )
        return {
            brand.id: count
            for brand, count in request.env["product.template"]
            .sudo()
            ._read_group(domain, ["product_brand_id"], ["__count"])
        }

    def _get_available_brands(self, domain, selected_brand_ids=None):
        selected_brand_ids = selected_brand_ids or []
        brand_model = request.env["product.brand"].sudo()
        brand_counts = self._get_product_counts_by_brand_ids(domain)
        brand_ids = list(brand_counts)
        brands = brand_model.browse(brand_ids)
        brands |= brand_model.search(
            Domain.AND(
                [
                    brand_model._website_public_domain(),
                    [("show_without_published_products", "=", True)],
                ]
            )
        )
        selected_brand_ids = [
            brand_id for brand_id in selected_brand_ids if brand_id not in brand_ids
        ]
        if selected_brand_ids:
            selected_brands = brand_model.search(
                Domain.AND(
                    [
                        brand_model._website_public_domain(),
                        [
                            ("id", "in", selected_brand_ids),
                        ],
                    ]
                )
            )
            brands |= selected_brands
        return brands.sorted("name"), brand_counts

    def _get_brand_letters(self, brands, brand_counts, selected_brand_ids):
        letters = {}
        for brand in brands:
            letter = (brand.name or "#")[0].upper()
            if not letter.isalpha():
                letter = "#"
            values = letters.setdefault(
                letter,
                {
                    "letter": letter,
                    "key": letter if letter != "#" else "other",
                    "count": 0,
                    "active": False,
                    "brands": request.env["product.brand"],
                    "has_more": False,
                },
            )
            values["count"] += brand_counts.get(brand.id, 0)
            if brand.id in selected_brand_ids:
                values["active"] = True
                values["brands"] |= brand
        return [letters[letter] for letter in sorted(letters)]

    def _get_brand_filter_values(self, domain, selected_brand_ids):
        mode = request.env.website.brand_filter_display_mode
        brands, brand_counts = self._get_available_brands(domain, selected_brand_ids)
        values = {
            "brand_filter_display_mode": mode,
            "brand_filter_limit": self.BRAND_LIMIT,
            "brand_letter_limit": self.BRAND_LETTER_LIMIT,
            "brand_has_more": False,
            "brand_letters": [],
        }
        if mode == "limited":
            selected_brands = brands.filtered(lambda b: b.id in selected_brand_ids)
            first_brands = brands[: self.BRAND_LIMIT]
            visible_brands = (selected_brands | first_brands).sorted("name")
            values.update(
                {
                    "brands": visible_brands,
                    "brand_has_more": len(brands - visible_brands) > 0,
                    "brand_next_offset": 0,
                }
            )
        elif mode == "letters":
            values.update(
                {
                    "brands": brands,
                    "brand_letters": self._get_brand_letters(
                        brands, brand_counts, selected_brand_ids
                    ),
                }
            )
        else:
            values["brands"] = brands
        return values

    def _get_brand_rpc_domain(self, search="", category_id=None, attribute_values=None):
        """Shop domain without the brand filter, for the brand filter RPCs.

        ``attribute_values`` is the dict of the shop attribute query params
        (``{"color-1": "red-2,blue-3"}``, Odoo 20) or a list in the legacy
        ``["<attribute_id>-<value_id>,<value_id>"]`` format."""
        category = None
        if category_id:
            category = request.env["product.public.category"].browse(int(category_id))
        attribute_values = attribute_values or {}
        if isinstance(attribute_values, (list, tuple)):
            attribute_values = dict(
                pair.split("-")
                for pair in attribute_values
                if pair and pair.count("-") == 1
            )
        else:
            attribute_values = self._get_attribute_value_params(attribute_values)
        attribute_value_dict = self._get_attribute_value_dict(attribute_values)
        return self._get_shop_domain_no_brands(
            search,
            category,
            attribute_value_dict,
            search_in_description=False,
        )

    def _get_selected_brand_ids_from_request(self, brand_ids=None):
        return self._as_int_list(brand_ids or [])

    def _render_brand_items(self, brands, selected_brand_ids):
        return request.env["ir.ui.view"]._render_template(
            "website_sale_product_brand.brand_filter_items",
            {
                "brands": brands,
                "selected_brand_ids": selected_brand_ids,
            },
        )

    def _get_shop_domain_no_brands(
        self,
        search,
        category,
        attribute_value_dict,
        search_in_description,
        tags=None,
    ):
        return super()._get_shop_domain(
            search,
            category,
            attribute_value_dict,
            search_in_description=search_in_description,
            tags=tags,
        )

    def _remove_extra_brands(self, brands, search_products, attrib_values):
        if attrib_values:
            search_product_brands = search_products.mapped("product_brand_id")
            brands = brands.filtered(lambda b: b.id in search_product_brands.ids)
        # sort brands by name
        return brands.sorted(key=lambda brand: brand.name)

    def _get_search_options(
        self,
        category=None,
        attribute_value_dict=None,
        tags=None,
        min_price=0.0,
        max_price=0.0,
        conversion_rate=1,
        **post,
    ):
        res = super()._get_search_options(
            category=category,
            attribute_value_dict=attribute_value_dict,
            tags=tags,
            min_price=min_price,
            max_price=max_price,
            conversion_rate=conversion_rate,
            **post,
        )
        res["brand_ids"] = request.env.context.get("brand_ids")
        return res

    def _get_shop_domain(
        self,
        search,
        category,
        attribute_value_dict,
        search_in_description=True,
        tags=None,
    ):
        domain = super()._get_shop_domain(
            search,
            category,
            attribute_value_dict,
            search_in_description=search_in_description,
            tags=tags,
        )
        brand_ids = request.env.context.get("brand_ids") or self._get_brand_ids(
            request.httprequest.args
        )
        if brand_ids:
            domain = Domain.AND([domain, [("product_brand_id", "in", brand_ids)]])
        return domain

    def _shop_get_query_url_kwargs(self, search, min_price, max_price, **kwargs):
        """Keep the selected brands in the shop links (pager, sort, filters...)."""
        res = super()._shop_get_query_url_kwargs(search, min_price, max_price, **kwargs)
        brand_ids = request.env.context.get("brand_ids")
        if brand_ids:
            res["brand"] = ",".join(str(brand_id) for brand_id in brand_ids)
        return res

    def _redirect_shop_brands_to_landing(self, fallback_brand=None):
        """
        When accessing `/shop/brands` with a `brand` or `brand_ids`
        query parameter, redirect to the corresponding brand landing page
        if the brand is published on the website.
        This allows external links to `/shop/brands?brand=1` to be redirected
        to the brand landing page, and also allows the shop page to redirect
        to the brand landing page when a brand is selected from the brands list.
        """
        if not request.httprequest.path.endswith(f"{SHOP_PATH}/brands"):
            return None

        landing_brand = self._get_brand_from_query(
            request.httprequest.args, fallback_brand
        )
        if not landing_brand:
            return None
        if not self._brand_visible_on_website(landing_brand):
            raise request.not_found()

        query_args = request.httprequest.args.to_dict(flat=False)
        query_args.pop("brand", None)
        query_args.pop("brand_ids", None)
        query = urlencode(query_args, doseq=True)
        target = landing_brand.website_url
        if query:
            target = f"{target}?{query}"
        return request.redirect(target, code=301)

    def _get_landing_brand_from_referrer(self, brand_ids):
        """On `/shop/reload` (AJAX filtering), detect that the page being
        filtered is a brand landing page, to keep its header."""
        if request.httprequest.path != "/shop/reload" or len(brand_ids) != 1:
            return request.env["product.brand"]
        referrer = request.httprequest.referrer or ""
        path = urlsplit(referrer).path
        if not path.startswith(f"{SHOP_PATH}/brand/"):
            return request.env["product.brand"]
        brand = self._get_brand_from_slug(path.split("/")[3])
        if brand.id != brand_ids[0] or not self._brand_visible_on_website(brand):
            return request.env["product.brand"]
        return brand

    @route()
    def shop(
        self,
        page=0,
        category=None,
        search="",
        min_price=0.0,
        max_price=0.0,
        tags="",
        on_sale=None,
        in_stock=None,
        brand=None,
        **post,
    ):
        brands_list = self._as_int_list(
            self._get_brand_ids(request.httprequest.args) + self._as_int_list(brand)
        )
        if brands_list:
            request.update_context(brand_ids=brands_list)
            # keep the brands in the pager links (built from ``post``)
            post["brand"] = ",".join(str(brand_id) for brand_id in brands_list)
        res = super().shop(
            page=page,
            category=category,
            search=search,
            min_price=min_price,
            max_price=max_price,
            tags=tags,
            on_sale=on_sale,
            in_stock=in_stock,
            **post,
        )
        qcontext = getattr(res, "qcontext", None)
        if not qcontext or qcontext.get("products") is None:
            return res
        domain = self._get_shop_domain_no_brands(
            qcontext.get("search") or "",
            qcontext.get("category"),
            qcontext.get("attrib_values") or {},
            search_in_description=False,
        )
        current_category = qcontext.get("category")
        qcontext.update(
            {
                "selected_brand_ids": brands_list,
                "brand_filter_category_id": current_category.id
                if current_category
                else False,
                **self._get_brand_filter_values(domain, brands_list),
            }
        )
        landing_brand = self._get_landing_brand_from_referrer(brands_list)
        if landing_brand and "landing_brand" not in qcontext:
            qcontext.update(
                {"landing_brand": landing_brand, "main_object": landing_brand}
            )
        return res

    @route(["/shop/brands"], type="http", auth="public", website=True, sitemap=False)
    def shop_brands(self, brand=None, **post):
        redirect_response = self._redirect_shop_brands_to_landing(brand)
        if redirect_response is not None:
            return redirect_response
        return self.shop(brand=brand, **post)

    def _landing_url(self, url, brand):
        """Move a shop URL (pager link) onto the brand landing page."""
        if not isinstance(url, str):
            return url
        path, sep, query = url.partition("?")
        if path == SHOP_PATH or path.startswith(f"{SHOP_PATH}/page/"):
            path = brand.website_url + path[len(SHOP_PATH) :]
        return f"{path}{sep}{query}"

    def _set_landing_links(self, qcontext, brand):
        pager = qcontext.get("pager")
        if pager:
            for value in pager.values():
                entries = value if isinstance(value, list) else [value]
                for entry in entries:
                    if isinstance(entry, dict) and "url" in entry:
                        entry["url"] = self._landing_url(entry["url"], brand)
        keep = qcontext.get("keep")
        if isinstance(keep, QueryURL) and keep.path == SHOP_PATH:
            qcontext["keep"] = QueryURL(
                brand.website_url, path_args=keep.path_args, **keep.args
            )

    @route(
        [
            f"{SHOP_PATH}/brand/<string:brand_slug>",
            f"{SHOP_PATH}/brand/<string:brand_slug>/page/<int:page>",
        ],
        type="http",
        auth="public",
        website=True,
        sitemap=sitemap_brands,
    )
    def shop_brand(
        self,
        brand_slug,
        page=0,
        search="",
        min_price=0.0,
        max_price=0.0,
        tags="",
        **post,
    ):
        brand = self._get_brand_from_slug(brand_slug)

        if not request.env.website.has_ecommerce_access():
            return request.redirect(f"/web/login?redirect={request.httprequest.path}")
        if not self._brand_visible_on_website(brand):
            raise request.not_found()

        self._set_current_brand(brand)
        post.pop("brand", None)
        post.pop("brand_ids", None)
        try:
            response = self.shop(
                page=page,
                category=None,
                search=search,
                min_price=min_price,
                max_price=max_price,
                tags=tags,
                brand=str(brand.id),
                **post,
            )
            if hasattr(response, "qcontext"):
                response.qcontext.update(
                    {
                        "landing_brand": brand,
                        "main_object": brand,
                    }
                )
                self._set_landing_links(response.qcontext, brand)
            return response
        finally:
            self._clear_current_brand()

    @route(
        ["/shop/brand_filter/load_more"],
        type="jsonrpc",
        auth="public",
        website=True,
    )
    def brand_filter_load_more(
        self,
        offset=0,
        limit=None,
        search="",
        category_id=None,
        attribute_values=None,
        brand_ids=None,
        exclude_brand_ids=None,
        **post,
    ):
        limit = int(limit or self.BRAND_LIMIT)
        selected_brand_ids = self._get_selected_brand_ids_from_request(brand_ids)
        exclude_brand_ids = self._get_selected_brand_ids_from_request(exclude_brand_ids)
        domain = self._get_brand_rpc_domain(search, category_id, attribute_values)
        all_brands, _brand_counts = self._get_available_brands(
            domain, selected_brand_ids
        )
        all_brands -= all_brands.filtered(lambda b: b.id in exclude_brand_ids)
        brands = all_brands[int(offset) : int(offset) + limit]
        return {
            "html": self._render_brand_items(brands, selected_brand_ids),
            "has_more": int(offset) + limit < len(all_brands),
            "next_offset": int(offset) + limit,
        }

    @route(
        ["/shop/brand_filter/load_letter"],
        type="jsonrpc",
        auth="public",
        website=True,
    )
    def brand_filter_load_letter(
        self,
        letter,
        offset=0,
        limit=None,
        search="",
        category_id=None,
        attribute_values=None,
        brand_ids=None,
        **post,
    ):
        limit = int(limit or self.BRAND_LETTER_LIMIT)
        selected_brand_ids = self._get_selected_brand_ids_from_request(brand_ids)
        domain = self._get_brand_rpc_domain(search, category_id, attribute_values)
        brands, _brand_counts = self._get_available_brands(domain, selected_brand_ids)
        if letter == "#":
            brands = brands.filtered(lambda b: not (b.name or "#")[0].isalpha())
        else:
            brands = brands.filtered(
                lambda b: (b.name or "").upper().startswith(letter)
            )
        visible_brands = brands[int(offset) : int(offset) + limit]
        return {
            "html": self._render_brand_items(visible_brands, selected_brand_ids),
            "has_more": int(offset) + limit < len(brands),
            "next_offset": int(offset) + limit,
        }

    # Method to get the brands.
    @route(["/page/product_brands"], type="http", auth="public", website=True)
    def product_brands(self, **post):
        product_brand = request.env["product.brand"]
        domain = product_brand._website_public_domain()
        if post.get("search"):
            domain = Domain.AND([domain, [("name", "ilike", post.get("search"))]])
        brand_rec = (
            product_brand.sudo()
            .search(domain)
            .filtered(
                lambda x: x.published_products_count > 0
                or x.show_without_published_products
            )
        )

        keep = QueryURL("/page/product_brands", brand_id=[])
        values = {"brand_rec": brand_rec, "keep": keep}
        if post.get("search"):
            values.update({"search": post.get("search")})
        return request.render("website_sale_product_brand.product_brands", values)
