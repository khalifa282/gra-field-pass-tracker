# -*- coding: utf-8 -*-
from odoo import models, fields, api


class FieldPassLanguage(models.TransientModel):
    _name = "field.pass.language"
    _description = "Field Pass Language Settings"

    language = fields.Selection(
        selection=[("en_US", "English"), ("ar_001", "العربية (Arabic)")],
        string="Interface Language",
        required=True,
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        res["language"] = self.env.user.lang or "en_US"
        return res

    def action_apply(self):
        self.ensure_one()
        lang_code = self.language

        # Activate language if not active
        lang_rec = self.env["res.lang"].with_context(active_test=False).search(
            [("code", "=", lang_code)], limit=1)
        if lang_rec and not lang_rec.active:
            lang_rec.write({"active": True})

        # Apply to current user
        self.env.user.write({"lang": lang_code})

        # Return home action
        return {
            "type": "ir.actions.act_url",
            "url": "/web",
            "target": "self",
        }

    @api.model
    def get_or_create(self):
        return self.create({})