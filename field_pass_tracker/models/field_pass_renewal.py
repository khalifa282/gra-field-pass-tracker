# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError
from .field_pass_notifications import send_fp_notification

DOCUMENT_TYPES = [
    ('passport', 'Passport - الجواز'),
    ('residency', 'Residency - الإقامة'),
    ('civil_id', 'Civil ID - البطاقة المدنية'),
    ('driving_license', 'Driving License - رخصة القيادة'),
    ('driving_hse', 'Driving HSE Training - تدريب السلامة للسائق'),
    ('driving_authority', 'Driving Authority - تصريح القيادة'),
    # NOTE: PTW and KOC Laptop Pass moved to Pass Application/Renewal —
    # confirmed change, no longer Document Renewal types.
    ('registration', 'Registration - تسجيل المركبة'),
    ('third_party', '3rd Party Inspection - فحص طرف ثالث'),
    ('clearance', 'Clearance Certificate - شهادة الفحص KOC'),
]

DOC_ATTACH_MAP = {
    'passport': ('passport_validity', 'attachment_passport', 'attachment_passport_name'),
    'residency': ('residency_validity', 'attachment_residency', 'attachment_residency_name'),
    'civil_id': ('civil_id_validity', 'attachment_civil_id', 'attachment_civil_id_name'),
    'driving_license': ('driving_license_validity', 'attachment_driving_license', 'attachment_driving_license_name'),
    'driving_hse': ('driving_hse_training_date', 'attachment_driving_hse', 'attachment_driving_hse_name'),
    'driving_authority': ('driving_authority_validity', 'attachment_driving_authority', 'attachment_driving_authority_name'),
    'registration': ('registration_expiry_date', 'attachment_registration', 'attachment_registration_name'),
    'third_party': ('third_party_inspection_date', 'attachment_third_party', 'attachment_third_party_name'),
    'clearance': ('clearance_certificate_expiry', 'attachment_clearance', 'attachment_clearance_name'),
}


class FieldPassRenewal(models.Model):
    """
    Each record = one event in the renewal log.
    Multiple records per document = full history.
    """
    _name = 'field.pass.renewal'
    _description = 'Document Renewal Log'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'event_date desc'
    _rec_name = 'display_name'

    display_name = fields.Char(compute='_compute_display_name', store=True)

    # ── Links ─────────────────────────────────────────────────────────────────
    employee_id = fields.Many2one('field.pass.employee', string='Employee - الموظف',
                                   ondelete='cascade', tracking=True)
    vehicle_id = fields.Many2one('field.pass.vehicle', string='Vehicle - المركبة',
                                  ondelete='cascade', tracking=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    # ── Document ──────────────────────────────────────────────────────────────
    document_type = fields.Selection(DOCUMENT_TYPES,
                                      string='Document Type - نوع المستند',
                                      required=True, tracking=True)

    # ── Event (each row = one event) ──────────────────────────────────────────
    event_type = fields.Selection([
        ('submitted', 'Submitted - مقدم'),
        ('rejected', 'Rejected - مرفوض'),
        ('issued', 'Issued - صادر'),
    ], string='Status - الحالة', required=True, default='submitted', tracking=True)

    event_date = fields.Datetime(string='Date - التاريخ',
                                  default=fields.Datetime.now, readonly=True)
    event_by = fields.Many2one('res.users', string='By - بواسطة',
                                default=lambda self: self.env.user, readonly=True)

    # ── Rejection fields ──────────────────────────────────────────────────────
    rejection_reason = fields.Text(string='Remarks - ملاحظات', tracking=True)

    # ── Issued fields ─────────────────────────────────────────────────────────
    new_expiry_date = fields.Date(string='New Expiry Date - تاريخ الانتهاء الجديد',
                                   tracking=True)
    attachment_new = fields.Binary(string='New Document - المستند الجديد', attachment=True)
    attachment_new_name = fields.Char(string='New Document Filename')

    @api.depends('employee_id', 'vehicle_id', 'document_type', 'event_type')
    def _compute_display_name(self):
        for r in self:
            entity = r.employee_id.name if r.employee_id else (
                r.vehicle_id.plate_number if r.vehicle_id else '?')
            doc = dict(DOCUMENT_TYPES).get(r.document_type, '')
            evt = dict([('submitted','Submitted'),('rejected','Rejected'),
                        ('issued','Issued')]).get(r.event_type, '')
            r.display_name = f'{entity} - {doc} [{evt}]'

    @api.constrains('employee_id', 'vehicle_id')
    def _check_entity(self):
        for r in self:
            if r.employee_id and r.vehicle_id:
                raise ValidationError('Cannot link to both employee and vehicle.')
            if not r.employee_id and not r.vehicle_id:
                raise ValidationError('Must link to employee or vehicle.')

    def action_update_record(self):
        """When issued - update expiry and attachment on employee/vehicle."""
        self.ensure_one()
        if self.event_type != 'issued':
            return
        mapping = DOC_ATTACH_MAP.get(self.document_type)
        if not mapping:
            return
        expiry_field, attach_field, attach_name_field = mapping
        entity = self.employee_id or self.vehicle_id
        if not entity:
            return
        update_vals = {}
        if self.new_expiry_date:
            update_vals[expiry_field] = self.new_expiry_date
        if self.attachment_new:
            update_vals[attach_field] = self.attachment_new
            update_vals[attach_name_field] = self.attachment_new_name
        if update_vals:
            entity.write(update_vals)
            entity.message_post(
                body=f'✅ {dict(DOCUMENT_TYPES).get(self.document_type)} issued. '
                     f'New expiry: {self.new_expiry_date}. By: {self.env.user.name}',
                message_type='comment',
            )


class FieldPassRenewalWizard(models.TransientModel):
    _name = 'field.pass.renewal.wizard'
    _description = 'Renewal Wizard'
    _rec_name = 'display_name'

    display_name = fields.Char(compute='_compute_display_name', store=True)

    @api.depends('document_type', 'employee_id', 'vehicle_id')
    def _compute_display_name(self):
        doc_map = dict(DOCUMENT_TYPES)
        for r in self:
            doc = doc_map.get(r.document_type, r.document_type or 'Document Renewal')
            entity = r.employee_id.name if r.employee_id else (
                r.vehicle_id.plate_number if r.vehicle_id else '')
            r.display_name = f'{doc} - {entity}' if entity else doc

    document_type = fields.Selection(DOCUMENT_TYPES,
                                      string='Document Type - نوع المستند')
    entity_type = fields.Selection([('employee', 'Employee'), ('vehicle', 'Vehicle')],
                                    compute='_compute_entity_type', store=True)
    employee_id = fields.Many2one('field.pass.employee', string='Employee - الموظف')
    vehicle_id = fields.Many2one('field.pass.vehicle', string='Vehicle - المركبة')

    has_open_submission = fields.Boolean(
        compute='_compute_status', store=True)
    history_ids = fields.Many2many(
        'field.pass.renewal',
        'fp_renewal_wiz_hist_rel',
        'wizard_id', 'renewal_id',
        string='History',
        compute='_compute_status', store=True,
    )

    @api.depends('document_type')
    def _compute_entity_type(self):
        emp_types = [d[0] for d in DOCUMENT_TYPES[:8]]
        for r in self:
            r.entity_type = 'employee' if r.document_type in emp_types else 'vehicle'

    @api.depends('document_type', 'employee_id', 'vehicle_id', 'entity_type')
    def _compute_status(self):
        for r in self:
            if not r.document_type:
                r.has_open_submission = False
                r.history_ids = [(5, 0, 0)]
                continue
            entity = r.employee_id if r.entity_type == 'employee' else r.vehicle_id
            if not entity:
                r.has_open_submission = False
                r.history_ids = [(5, 0, 0)]
                continue
            domain = [('document_type', '=', r.document_type)]
            if r.entity_type == 'employee':
                domain.append(('employee_id', '=', r.employee_id.id))
            else:
                domain.append(('vehicle_id', '=', r.vehicle_id.id))
            renewals = self.env['field.pass.renewal'].search(
                domain, order='event_date desc')
            r.history_ids = [(6, 0, renewals.ids)]
            latest = renewals[0] if renewals else False
            r.has_open_submission = bool(latest and latest.event_type == 'submitted')

    def _get_entity_domain(self):
        if self.entity_type == 'employee' and self.employee_id:
            return [('employee_id', '=', self.employee_id.id)]
        elif self.entity_type == 'vehicle' and self.vehicle_id:
            return [('vehicle_id', '=', self.vehicle_id.id)]
        return []

    # NOTE: _new_wizard() was removed here — even after making it reuse
    # self.id instead of creating a new record, returning ANY act_window
    # action from a button push still stacked a new breadcrumb entry (this
    # is fundamental Odoo client behavior, not fixable via target/res_id
    # tricks). action_submit_renewal now just calls _compute_status() and
    # returns True directly instead.

    def action_submit_renewal(self):
        self.ensure_one()
        domain = self._get_entity_domain()
        if not domain:
            raise ValidationError('Please select an employee or vehicle.')

        _OK = ('valid', 'warning')

        # Prerequisite: domino chain (Passport -> Residency -> Civil ID ->
        # Driving License), matching the same rules now enforced on the
        # Employee model itself (field_pass_employee.py) — duplicated here
        # so Submit is gated the same way Issue already is, not just when
        # the Employee record itself gets written.
        if self.document_type == 'residency' and self.employee_id and not self.employee_id.gcc_national:
            if self.employee_id.passport_status not in _OK:
                raise ValidationError(
                    f'Cannot submit Residency renewal for "{self.employee_id.name}": '
                    f'Passport must be valid first.'
                )

        if self.document_type == 'civil_id' and self.employee_id:
            emp = self.employee_id
            if emp.gcc_national:
                if emp.passport_status not in _OK:
                    raise ValidationError(
                        f'Cannot submit Civil ID renewal for "{emp.name}": Passport must be valid first.'
                    )
            else:
                if emp.residency_status not in _OK:
                    raise ValidationError(
                        f'Cannot submit Civil ID renewal for "{emp.name}": Residency must be valid first.'
                    )

        if self.document_type == 'driving_license' and self.employee_id:
            if self.employee_id.civil_id_status not in _OK:
                raise ValidationError(
                    f'Cannot submit Driving License renewal for "{self.employee_id.name}": '
                    f'Civil ID must be valid first.'
                )

        if self.document_type == 'driving_hse' and self.employee_id:
            if self.employee_id.driving_license_status not in _OK:
                raise ValidationError(
                    f'Cannot submit Driving HSE Training renewal for "{self.employee_id.name}": '
                    f'Driving License must be valid first.'
                )

        # Prerequisite: Driving Authority requires issued HSE Training
        if self.document_type == 'driving_authority' and self.employee_id:
            hse = self.env['field.pass.renewal'].search([
                ('employee_id', '=', self.employee_id.id),
                ('document_type', '=', 'driving_hse'),
                ('event_type', '=', 'issued'),
            ], limit=1)
            if not hse and not self.employee_id.driving_hse_training_date:
                raise ValidationError(
                    f'Cannot submit Driving Authority renewal for "{self.employee_id.name}". '
                    f'Driving HSE Training must be completed and issued first.'
                )

        # NOTE: PTW and KOC Laptop Pass prerequisite checks removed here —
        # those document types no longer exist in Document Renewal (moved
        # to Pass Application/Renewal — see field_pass_renewal_wizard.py's
        # action_submit_application and field_pass.py).

        # Vehicle prerequisites
        if self.vehicle_id:
            from datetime import date as dt
            if self.document_type == 'third_party':
                reg = self.vehicle_id.registration_expiry_date
                if not reg or reg < dt.today():
                    raise ValidationError(
                        f'Cannot submit 3rd Party Inspection for "{self.vehicle_id.plate_number}". '
                        f'A valid Registration is required first.'
                    )
            if self.document_type == 'clearance':
                # FIX: previously only checked 3rd Party Inspection —
                # Registration must ALSO be valid, matching the actual
                # confirmed rule (both required, not just one).
                reg = self.vehicle_id.registration_expiry_date
                tp = self.vehicle_id.third_party_inspection_expiry
                missing = []
                if not reg or reg < dt.today():
                    missing.append('Registration')
                if not tp or tp < dt.today():
                    missing.append('3rd Party Inspection')
                if missing:
                    raise ValidationError(
                        f'Cannot submit Clearance Certificate for "{self.vehicle_id.plate_number}": '
                        f'the following must be valid first: {", ".join(missing)}.'
                    )

        # Check latest event — only block if latest is submitted
        latest = self.env['field.pass.renewal'].search(
            [('document_type', '=', self.document_type)] + domain,
            order='event_date desc', limit=1)
        if latest and latest.event_type == 'submitted':
            raise ValidationError(
                'There is already an open renewal. Please issue or reject it first.')
        vals = {
            'document_type': self.document_type,
            'event_type': 'submitted',
            'event_by': self.env.user.id,
        }
        if self.employee_id:
            vals['employee_id'] = self.employee_id.id
        else:
            vals['vehicle_id'] = self.vehicle_id.id
        self.env['field.pass.renewal'].create(vals)

        entity = self.employee_id or self.vehicle_id
        doc_label = dict(DOCUMENT_TYPES).get(self.document_type, self.document_type)
        send_fp_notification(
            self.env, entity, doc_label.split(' - ')[0], 'submitted',
            event_by_name=self.env.user.name,
        )

        # FIX: previously returned a full ir.actions.act_window dict (via
        # _new_wizard(), even after making it reuse self.id) — this STILL
        # stacked a new breadcrumb entry every time, because ANY act_window
        # action returned from a button push is treated by Odoo's client as
        # a real navigation event, regardless of target value or matching
        # res_id. The correct, standard Odoo pattern for "stay on this
        # screen, just refresh" is to return True (or nothing) instead —
        # no navigation occurs, so no breadcrumb is pushed. The explicit
        # _compute_status() call forces the stored compute fields
        # (has_open_submission, history) to update immediately, so the
        # form shows fresh data on reload.
        self._compute_status()
        return True

    def action_open_issue_wizard(self):
        self.ensure_one()
        domain = self._get_entity_domain()
        latest = self.env['field.pass.renewal'].search(
            [('document_type', '=', self.document_type)] + domain,
            order='event_date desc', limit=1)
        if not latest or latest.event_type != 'submitted':
            raise ValidationError('No open submission found.')
        return {
            'type': 'ir.actions.act_window',
            'name': 'Issue Document - إصدار المستند',
            'res_model': 'field.pass.renewal.issue.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_document_type': self.document_type,
                'default_entity_type': self.entity_type,
                'default_employee_id': self.employee_id.id if self.employee_id else False,
                'default_vehicle_id': self.vehicle_id.id if self.vehicle_id else False,
                'default_parent_wizard_id': self.id,
            },
        }

    def action_open_reject_wizard(self):
        self.ensure_one()
        domain = self._get_entity_domain()
        latest = self.env['field.pass.renewal'].search(
            [('document_type', '=', self.document_type)] + domain,
            order='event_date desc', limit=1)
        if not latest or latest.event_type != 'submitted':
            raise ValidationError('No open submission found.')
        return {
            'type': 'ir.actions.act_window',
            'name': 'Reject Renewal - رفض التجديد',
            'res_model': 'field.pass.renewal.reject.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_document_type': self.document_type,
                'default_entity_type': self.entity_type,
                'default_employee_id': self.employee_id.id if self.employee_id else False,
                'default_vehicle_id': self.vehicle_id.id if self.vehicle_id else False,
                'default_parent_wizard_id': self.id,
            },
        }


class FieldPassRenewalIssueWizard(models.TransientModel):
    _name = 'field.pass.renewal.issue.wizard'
    _description = 'Issue Document Wizard'

    document_type = fields.Char()
    entity_type = fields.Char()
    employee_id = fields.Many2one('field.pass.employee')
    vehicle_id = fields.Many2one('field.pass.vehicle')
    # NEW — reference back to the main Document Renewal wizard screen that
    # opened this popup, so action_confirm can return to the SAME record
    # instead of creating a new one (fixes breadcrumb stacking).
    parent_wizard_id = fields.Many2one('field.pass.renewal.wizard')
    new_expiry_date = fields.Date(
        string='New Expiry Date - تاريخ الانتهاء الجديد', required=True)
    attachment_new = fields.Binary(
        string='New Document - المستند الجديد', attachment=True)
    attachment_new_name = fields.Char(string='New Document Filename')

    def action_confirm(self):
        # Prerequisite: Driving Authority requires HSE Training
        if self.document_type == 'driving_authority' and self.employee_id:
            if not self.employee_id.driving_hse_training_date:
                raise ValidationError(
                    f'Cannot issue Driving Authority for "{self.employee_id.name}". '
                    f'Driving HSE Training must be completed first.'
                )
        # NOTE: this Driving Authority check previously appeared twice in a
        # row here (identical duplicate) — cleaned up as a pre-existing bug
        # unrelated to the PTW/KOC Laptop move. The PTW check that used to
        # sit here was removed — PTW is no longer a Document Renewal type.

        vals = {
            'document_type': self.document_type,
            'event_type': 'issued',
            'event_by': self.env.user.id,
            'new_expiry_date': self.new_expiry_date,
            'attachment_new': self.attachment_new,
            'attachment_new_name': self.attachment_new_name,
        }
        if self.employee_id:
            vals['employee_id'] = self.employee_id.id
        else:
            vals['vehicle_id'] = self.vehicle_id.id
        renewal = self.env['field.pass.renewal'].create(vals)
        renewal.action_update_record()

        entity = self.employee_id or self.vehicle_id
        doc_label = dict(DOCUMENT_TYPES).get(self.document_type, self.document_type)
        send_fp_notification(
            self.env, entity, doc_label.split(' - ')[0], 'issued',
            event_by_name=self.env.user.name,
            extra_note=f'New expiry date: {self.new_expiry_date}',
        )

        # FIX: force the parent's stored compute fields (has_open_submission,
        # history) to update immediately, then just CLOSE this popup —
        # returning act_window_close (not a new act_window action) tells
        # Odoo's client to dismiss the dialog and refresh the parent screen
        # underneath in place, with no breadcrumb impact at all.
        if self.parent_wizard_id:
            self.parent_wizard_id._compute_status()
        return {'type': 'ir.actions.act_window_close'}


class FieldPassRenewalRejectWizard(models.TransientModel):
    _name = 'field.pass.renewal.reject.wizard'
    _description = 'Reject Renewal Wizard'

    document_type = fields.Char()
    entity_type = fields.Char()
    employee_id = fields.Many2one('field.pass.employee')
    vehicle_id = fields.Many2one('field.pass.vehicle')
    parent_wizard_id = fields.Many2one('field.pass.renewal.wizard')
    rejection_reason = fields.Text(
        string='Rejection Reason - سبب الرفض', required=True)

    def action_confirm(self):
        vals = {
            'document_type': self.document_type,
            'event_type': 'rejected',
            'event_by': self.env.user.id,
            'rejection_reason': self.rejection_reason,
        }
        if self.employee_id:
            vals['employee_id'] = self.employee_id.id
        else:
            vals['vehicle_id'] = self.vehicle_id.id
        self.env['field.pass.renewal'].create(vals)

        entity = self.employee_id or self.vehicle_id
        doc_label = dict(DOCUMENT_TYPES).get(self.document_type, self.document_type)
        send_fp_notification(
            self.env, entity, doc_label.split(' - ')[0], 'rejected',
            event_by_name=self.env.user.name,
            extra_note=f'Reason: {self.rejection_reason}',
        )

        if self.parent_wizard_id:
            self.parent_wizard_id._compute_status()
        return {'type': 'ir.actions.act_window_close'}