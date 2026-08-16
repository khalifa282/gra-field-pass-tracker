# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError


class FieldPassHrResidencyRequest(models.Model):
    _name = 'field.pass.hr.residency.request'
    _description = 'HR Request — Residency Transfer'
    _order = 'create_date desc'

    def _require(self, checks):
        """
        checks: list of (value, label) tuples. Collects EVERY missing item
        into one error, rather than stopping at the first — confirmed
        design: someone fixing one field shouldn't have to resubmit
        repeatedly to discover the next missing one.
        """
        missing = [label for value, label in checks if not value]
        if missing:
            raise ValidationError(
                'Please complete the following before proceeding:\n- ' + '\n- '.join(missing)
            )

    def _notify_other_side(self, to_group, subject_suffix, extra=''):
        """
        Confirmed design: HR actions notify GRO, GRO actions notify HR —
        symmetric in both directions, at every stage transition.
        to_group: 'field_pass_tracker.group_fp_viewer' (GRO) or
        'field_pass_tracker.group_fp_hr_viewer' (HR) — base tier group,
        Admin/Manager auto-included via implied_ids.
        """
        self.ensure_one()
        from .field_pass_notifications import notify_track
        subject = f'Residency Transfer {self.name} — {subject_suffix}'
        body_html = (
            f'<p><b>{self.name}</b> — {self.candidate_name}</p>'
            f'<p>{subject_suffix}</p>'
        )
        if extra:
            body_html += f'<p>{extra}</p>'
        notify_track(self.env, to_group, subject, body_html)

    name = fields.Char(default='New', readonly=True, copy=False)

    # ── Candidate details — entered once at Check stage, reused unchanged
    # through the Transfer stage (confirmed: same record, same data). ──────
    candidate_name = fields.Char(string='Candidate Name (English)', required=True)
    candidate_name_ar = fields.Char(string='اسم الموظف بالعربي')
    civil_id = fields.Char(string='Civil ID - البطاقة المدنية', required=True)
    company_id = fields.Many2one(
        'field.pass.company', string='Company - الشركة', required=True)
    department_id = fields.Many2one(
        'hr.department', string='Department - القسم', required=True,
        domain="[('fp_company_id', '=', company_id)]",
        help='Filtered to departments belonging to the selected Company.',
    )
    internal_position_title = fields.Char(string='Position Title - المسمى الوظيفي')
    suggested_position_title = fields.Char(
        string='Suggested Work Permit Position Title - المسمى الوظيفي المقترح لإذن العمل')
    candidate_contact_no = fields.Char(string='Candidate Contact No - رقم اتصال المرشح')

    # ── Check-stage attachments ──────────────────────────────────────────────
    attachment_passport = fields.Binary(string='Passport - جواز السفر', attachment=True)
    attachment_passport_name = fields.Char()
    attachment_civil_id = fields.Binary(string='Civil ID - البطاقة المدنية', attachment=True)
    attachment_civil_id_name = fields.Char()
    attachment_work_permit = fields.Binary(string='Work Permit - إذن العمل', attachment=True)
    attachment_work_permit_name = fields.Char()
    attachment_driving_license = fields.Binary(string='Driving License (Optional) - رخصة القيادة (اختياري)', attachment=True)
    attachment_driving_license_name = fields.Char()
    attachment_education_cert = fields.Binary(string='Education Certificate - الشهادة الدراسية', attachment=True)
    attachment_education_cert_name = fields.Char()

    # ── Check-stage GRO response ─────────────────────────────────────────────
    transferable = fields.Selection([
        ('yes', 'Yes - نعم'), ('no', 'No - لا'),
    ], string='Transferable? - قابل للتحويل؟')
    transferable_comments = fields.Text(string='Comments - ملاحظات')

    # ── Transfer-stage addition — the ONLY new field HR adds when
    # continuing the same request (confirmed design). ───────────────────────
    salary = fields.Float(string='Salary - الراتب')

    # ── Transfer-stage GRO resolution ────────────────────────────────────────
    rejection_reason = fields.Text(string='Rejection Reason - سبب الرفض')
    attachment_final_work_permit = fields.Binary(string='Work Permit - اذن العمل', attachment=True)
    attachment_final_work_permit_name = fields.Char()
    attachment_health_insurance = fields.Binary(string='Health Insurance - الضمان الصحي', attachment=True)
    attachment_health_insurance_name = fields.Char()
    attachment_moi_migration = fields.Binary(string='MOI Migration - الهجرة', attachment=True)
    attachment_moi_migration_name = fields.Char()
    attachment_final_civil_id = fields.Binary(string='Civil ID - البطاقة المدنية', attachment=True)
    attachment_final_civil_id_name = fields.Char()

    state = fields.Selection([
        ('draft', 'Draft - مسودة'),
        ('check_submitted', 'Check Submitted - تم تقديم الفحص'),
        ('check_done', 'Check Done - تم الفحص'),
        ('transfer_submitted', 'Transfer Submitted - تم تقديم طلب النقل'),
        ('rejected', 'Rejected - مرفوض'),
        ('under_process', 'Under Process - قيد المعالجة'),
        ('completed', 'Completed - مكتمل'),
    ], default='draft', required=True, tracking=True)

    history_ids = fields.One2many(
        'field.pass.hr.residency.request.log', 'request_id', string='History - السجل')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'field.pass.hr.residency.request') or 'New'
        return super().create(vals_list)

    def _log(self, event_type, notes=''):
        self.ensure_one()
        self.env['field.pass.hr.residency.request.log'].create({
            'request_id': self.id,
            'event_type': event_type,
            'event_by': self.env.user.id,
            'notes': notes,
        })

    # ── Stage A: Check ────────────────────────────────────────────────────────
    def action_submit_check(self):
        self.ensure_one()
        if self.state != 'draft':
            raise UserError('This request has already been submitted for checking.')
        self._require([
            (self.candidate_name, 'Candidate Name (English)'),
            (self.candidate_name_ar, 'اسم الموظف بالعربي'),
            (self.civil_id, 'Civil ID - البطاقة المدنية'),
            (self.company_id, 'Company - الشركة'),
            (self.department_id, 'Department - القسم'),
            (self.internal_position_title, 'Position Title - المسمى الوظيفي'),
            (self.suggested_position_title, 'Suggested Work Permit Position Title'),
            (self.candidate_contact_no, 'Candidate Contact No - رقم اتصال المرشح'),
            (self.attachment_passport, 'Passport - جواز السفر (upload)'),
            (self.attachment_civil_id, 'Civil ID - البطاقة المدنية (upload)'),
            (self.attachment_work_permit, 'Work Permit - إذن العمل (upload)'),
            (self.attachment_education_cert, 'Education Certificate - الشهادة الدراسية (upload)'),
            # Driving License stays optional by design — not included here.
        ])
        self.state = 'check_submitted'
        self._log('check_submitted')
        self._notify_other_side('field_pass_tracker.group_fp_viewer', 'New Check Request Submitted')

    def action_open_check_wizard(self):
        self.ensure_one()
        if self.state != 'check_submitted':
            raise UserError('This request is not awaiting a check response.')
        return {
            'type': 'ir.actions.act_window',
            'name': 'GRO Response - رد الجهة الحكومية',
            'res_model': 'field.pass.hr.residency.check.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_request_id': self.id},
        }

    def action_gro_respond_check(self, transferable, comments=''):
        """Called from the GRO response form (Stage 2B wizard/inline fields).

        Confirmed: a 'No' answer must actually STOP the process — not just
        hide the next button while leaving the record in an ambiguous
        state. 'No' now closes the request directly as Rejected (reusing
        the same terminal state and Reopen mechanism already built for
        transfer-stage rejections), rather than landing in check_done with
        nothing to click. 'Yes' proceeds normally.
        """
        self.ensure_one()
        if self.state != 'check_submitted':
            raise UserError('This request is not awaiting a check response.')
        if transferable == 'no':
            self.write({
                'transferable': transferable,
                'transferable_comments': comments,
                'state': 'rejected',
                'rejection_reason': f'Not transferable: {comments}' if comments else 'Not transferable.',
            })
            self._log('rejected', notes=f'Not transferable. {comments}')
            self._notify_other_side('field_pass_tracker.group_fp_hr_viewer', 'Not Transferable — Rejected', comments)
            return
        self.write({
            'transferable': transferable,
            'transferable_comments': comments,
            'state': 'check_done',
        })
        self._log('check_done', notes=f'Transferable: {transferable}. {comments}')
        self._notify_other_side('field_pass_tracker.group_fp_hr_viewer', 'Check Completed — Transferable', comments)

    # ── Stage B: Transfer (HR reopens the SAME record, adds Salary) ────────────
    def action_submit_transfer(self):
        self.ensure_one()
        if self.state != 'check_done':
            raise UserError('The check stage must be completed before requesting the transfer.')
        if self.transferable != 'yes':
            raise UserError(
                'This candidate was marked as NOT transferable — the process stops here. '
                'A transfer request cannot be submitted.'
            )
        if not self.salary:
            raise ValidationError('Salary is required to submit the transfer request.')
        self.state = 'transfer_submitted'
        self._log('transfer_submitted', notes=f'Salary: {self.salary}')
        self._notify_other_side('field_pass_tracker.group_fp_viewer', 'Transfer Request Submitted')

    def action_open_reject_wizard(self):
        self.ensure_one()
        if self.state != 'transfer_submitted':
            raise UserError('Only a submitted transfer request can be rejected.')
        return {
            'type': 'ir.actions.act_window',
            'name': 'Reject Request - رفض الطلب',
            'res_model': 'field.pass.hr.residency.reject.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_request_id': self.id},
        }

    def action_reject(self, reason):
        self.ensure_one()
        if self.state != 'transfer_submitted':
            raise UserError('Only a submitted transfer request can be rejected.')
        self.write({'rejection_reason': reason, 'state': 'rejected'})
        self._log('rejected', notes=reason)
        self._notify_other_side('field_pass_tracker.group_fp_hr_viewer', 'Rejected', reason)

    def action_mark_under_process(self):
        self.ensure_one()
        if self.state != 'transfer_submitted':
            raise UserError('Only a submitted transfer request can move to Under Process.')
        self.state = 'under_process'
        self._log('under_process')
        self._notify_other_side('field_pass_tracker.group_fp_hr_viewer', 'Under Process')

    def action_complete(self):
        self.ensure_one()
        if self.state != 'under_process':
            raise UserError('Only a request Under Process can be marked Completed.')
        self._require([
            (self.attachment_final_work_permit, 'Work Permit - اذن العمل (upload)'),
            (self.attachment_health_insurance, 'Health Insurance - الضمان الصحي (upload)'),
            (self.attachment_moi_migration, 'MOI Migration - الهجرة (upload)'),
            (self.attachment_final_civil_id, 'Civil ID - البطاقة المدنية (upload)'),
        ])
        self.state = 'completed'
        self._log('completed')
        self._notify_other_side('field_pass_tracker.group_fp_hr_viewer', 'Completed')
        self._create_employee_record()

    def _create_employee_record(self):
        """
        Confirmed design: Completing a Residency Transfer means a new Civil
        ID now exists, and this is the trigger point to create the actual
        Employee record — HR Request stays a one-time onboarding record;
        Employee becomes the ongoing source of truth from here on (future
        renewals/changes happen on the Employee record, never fed back to
        this request).

        Only the fields genuinely shared between both models are copied —
        deliberately NOT a full field-by-field mirror (see the comparison
        discussion: Salary, Contact No, etc. have no home on Employee and
        stay only on this request). Company is intentionally left at
        Employee's own default — Employee.company_id is Odoo's native
        res.company, a different concept from this request's
        field.pass.company, with no automatic mapping between the two.
        """
        self.ensure_one()
        Employee = self.env['field.pass.employee']
        vals = {
            'name': self.candidate_name,
            'name_ar': self.candidate_name_ar,
            'department_id': self.department_id.id,
            'designation': self.internal_position_title,
        }
        # Prefer the completion-stage Civil ID (the new, actual one) over
        # the check-stage copy, if it was uploaded.
        if self.attachment_final_civil_id:
            vals['attachment_civil_id'] = self.attachment_final_civil_id
            vals['attachment_civil_id_name'] = self.attachment_final_civil_id_name
        elif self.attachment_civil_id:
            vals['attachment_civil_id'] = self.attachment_civil_id
            vals['attachment_civil_id_name'] = self.attachment_civil_id_name
        if self.attachment_passport:
            vals['attachment_passport'] = self.attachment_passport
            vals['attachment_passport_name'] = self.attachment_passport_name
        if self.attachment_driving_license:
            vals['attachment_driving_license'] = self.attachment_driving_license
            vals['attachment_driving_license_name'] = self.attachment_driving_license_name
        employee = Employee.create(vals)
        self._log('employee_created', notes=f'Employee record created: {employee.name} (#{employee.id})')

    def action_reopen(self):
        """
        Confirmed design: Rejected is NOT a permanent dead end — HR can
        reopen the same request to try again. Two different origins now
        need two different landing spots:
        - A genuine transfer-stage rejection (transferable was 'yes', but
          the Transfer request itself got rejected later) -> back to
          'check_done', matching the original design — the check itself
          was fine, only the transfer attempt needs retrying.
        - A 'not transferable' rejection (transferable is 'no') -> back to
          'check_submitted' instead, since the CHECK itself is what
          concluded negatively — HR needs a fresh GRO response, not a
          shortcut straight to a transfer attempt that's still blocked.
          transferable/comments are cleared so the next response is a
          clean, fresh answer.
        The old rejection_reason is cleared from the live field either way
        (it stays visible forever in History, just not shown as the
        "current" reason once no longer rejected).
        """
        self.ensure_one()
        if self.state != 'rejected':
            raise UserError('Only a rejected request can be reopened.')
        old_reason = self.rejection_reason
        if self.transferable == 'no':
            self.write({
                'rejection_reason': False,
                'transferable': False,
                'transferable_comments': False,
                'state': 'check_submitted',
            })
        else:
            self.write({'rejection_reason': False, 'state': 'check_done'})
        self._log('reopened', notes=f'Previous rejection reason: {old_reason}')
        self._notify_other_side('field_pass_tracker.group_fp_viewer', 'Reopened')


class FieldPassHrResidencyRequestLog(models.Model):
    _name = 'field.pass.hr.residency.request.log'
    _description = 'Residency Transfer Request — Event Log'
    _order = 'event_date desc'

    request_id = fields.Many2one(
        'field.pass.hr.residency.request', required=True, ondelete='cascade', index=True)
    event_type = fields.Selection([
        ('check_submitted', 'Check Submitted'),
        ('check_done', 'Check Done'),
        ('transfer_submitted', 'Transfer Submitted'),
        ('rejected', 'Rejected'),
        ('reopened', 'Reopened'),
        ('under_process', 'Under Process'),
        ('completed', 'Completed'),
        ('employee_created', 'Employee Record Created'),
    ], required=True)
    event_date = fields.Datetime(default=fields.Datetime.now, required=True)
    event_by = fields.Many2one('res.users', default=lambda self: self.env.user, required=True)
    notes = fields.Text()


# ── Small confirmation popups — same pattern as the Renewal/Application
# Reject/Issue wizards elsewhere in this module: the main record's action
# methods need extra input (Transferable+Comments, or a Rejection Reason)
# that can't bind directly to a simple button, so a small popup collects it
# and calls back into the main record. ──────────────────────────────────────

class FieldPassHrResidencyCheckWizard(models.TransientModel):
    _name = 'field.pass.hr.residency.check.wizard'
    _description = 'GRO Response — Residency Transfer Check'

    request_id = fields.Many2one('field.pass.hr.residency.request', required=True)
    transferable = fields.Selection([
        ('yes', 'Yes - نعم'), ('no', 'No - لا'),
    ], string='Transferable? - قابل للتحويل؟', required=True)
    comments = fields.Text(string='Comments - ملاحظات', required=True)

    def action_confirm(self):
        self.ensure_one()
        self.request_id.action_gro_respond_check(self.transferable, self.comments)
        return {'type': 'ir.actions.act_window_close'}


class FieldPassHrResidencyRejectWizard(models.TransientModel):
    _name = 'field.pass.hr.residency.reject.wizard'
    _description = 'Reject — Residency Transfer Request'

    request_id = fields.Many2one('field.pass.hr.residency.request', required=True)
    reason = fields.Text(string='Rejection Reason - سبب الرفض', required=True)

    def action_confirm(self):
        self.ensure_one()
        self.request_id.action_reject(self.reason)
        return {'type': 'ir.actions.act_window_close'}
