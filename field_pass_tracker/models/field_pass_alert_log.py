# -*- coding: utf-8 -*-
from odoo import models, fields, api


class FieldPassAlertLog(models.Model):
    _name = 'field.pass.alert.log'
    _description = 'Field Pass Notification Log'
    _order = 'sent_date desc'

    # ── What this alert was about ────────────────────────────────────────────
    res_model = fields.Char(
        required=True, index=True,
        help="Technical model name the alert relates to: "
             "field.pass.employee / field.pass.vehicle / field.pass.",
    )
    res_id = fields.Integer(required=True, index=True)
    entity_name = fields.Char(
        help="Denormalized employee/vehicle name — for easy log browsing "
             "without needing to resolve res_id, and survives even if the "
             "underlying record is later deleted.",
    )
    department_id = fields.Many2one(
        'hr.department', help="Denormalized for easy filtering of the log by department.")
    document_type = fields.Char(
        required=True,
        help="Which document or pass type this alert is about "
             "(e.g. 'passport', 'civil_id', 'KOC', 'WAFRA', ...).",
    )

    # ── What kind of alert, and for which expiry cycle ───────────────────────
    alert_type = fields.Selection([
        ('submitted', 'Submitted'),
        ('rejected', 'Rejected'),
        ('issued', 'Issued'),
        ('warning', 'Warning'),
        ('expired', 'Expired'),
    ], required=True, index=True)
    # IMPORTANT: for warning/expired specifically, this is what makes the
    # dedup check correct across renewal cycles. Without it, a document
    # renewed with a NEW expiry date would never alert again after the
    # first time it ever went into warning/expired — the dedup would
    # incorrectly treat "already alerted once, ever" as permanent. Scoping
    # by the specific expiry date means each renewal cycle gets its own
    # fresh warning/expired check. Left blank for submitted/rejected/issued
    # (those are discrete one-off events, no dedup needed for them at all —
    # see the note on already_sent() below).
    document_expiry_date = fields.Date()

    sent_date = fields.Datetime(default=fields.Datetime.now, required=True)
    recipient_emails = fields.Char(help="Who actually got emailed — for troubleshooting delivery issues.")

    @api.model
    def already_sent(self, res_model, res_id, document_type, alert_type, expiry_date=None):
        """
        Dedup check — has this exact alert already been sent?

        Only meaningfully used for 'warning'/'expired' (called by the daily
        cron before sending, so a missed cron day can safely catch up
        without double-sending). 'submitted'/'rejected'/'issued' don't
        need this check at all — those are triggered directly from a
        one-time user action (Submit/Reject/Issue button), so there's
        nothing to accidentally repeat; callers for those simply create a
        log row without calling this first.
        """
        domain = [
            ('res_model', '=', res_model),
            ('res_id', '=', res_id),
            ('document_type', '=', document_type),
            ('alert_type', '=', alert_type),
        ]
        if expiry_date:
            domain.append(('document_expiry_date', '=', expiry_date))
        return bool(self.search_count(domain))
