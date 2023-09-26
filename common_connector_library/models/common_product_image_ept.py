# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.
import base64
import requests
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class ProductImageEpt(models.Model):
    _name = 'common.product.image.ept'
    _description = 'common.product.image.ept'
    _order = 'sequence, id'

    name = fields.Char()
    product_id = fields.Many2one('product.product', ondelete='cascade')
    template_id = fields.Many2one('product.template', string='Product template', ondelete='cascade')
    image = fields.Image()
    url = fields.Char(string="Image URL", help="External URL of image")
    sequence = fields.Integer(help="Sequence of images.", index=True, default=10)

    @api.model
    def get_image_ept(self, url, verify=False):
        """
        Gets image from url.
        @author: Maulik Barad on Date 13-Dec-2019.
        @param url: URL added in field.
        Migration done by Haresh Mori on September 2021
        """
        image_types = ["image/jpeg", "image/png", "image/tiff",
                       "image/vnd.microsoft.icon", "image/x-icon",
                       "image/vnd.djvu", "image/svg+xml", "image/gif"]
        response = requests.get(url, stream=True, verify=verify, timeout=10)
        if response.status_code == 200 and response.headers["Content-Type"] in image_types:
            image = base64.b64encode(response.content)
            if image:
                return image
        raise UserError(_("Can't find image.\nPlease provide valid Image URL."))

    @api.model
    def default_get(self, fields):
        """
        We have inherited default_get method for setting default value of template_id and product_id in context for
        select variant wise images.Added this method because it does not display variants in common product image form view
        @author: Hardik Dhankecha on date 02-Apr-2021.
        Migration done by Haresh Mori on September 2021,
        """
        fields += ["template_id", "product_id"]
        return super(ProductImageEpt, self).default_get(fields)

    @api.model
    def create(self, vals):
        """
        Inherited for adding image from URL.
        @author: Maulik Barad on date 13-Dec-2019.
        Migration done by Haresh Mori on September 2021
        """
        verify = False
        ir_config_parameter_obj = self.env['ir.config_parameter']
        if not vals.get("image", False) and vals.get("url", ""):
            if 'ssl_verify' in list(self.env.context.keys()):
                verify = True
            image = self.get_image_ept(vals.get("url"), verify=verify)
            vals.update({"image": image})
        record = super(ProductImageEpt, self).create(vals)

        base_url = ir_config_parameter_obj.sudo().get_param('web.base.url')
        rec_id = str(record.id)
        url = base_url + '/lf/i/%s' % (base64.urlsafe_b64encode(rec_id.encode("utf-8")).decode("utf-8"))
        record.write({'url': url})
        return record
