# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError


class FieldPassHrVisaRequest(models.Model):
    _name = 'field.pass.hr.visa.request'
    _description = 'HR Request — Issue a Work Visa'
    _order = 'create_date desc'

    def _require(self, checks):
        """Same pattern as the Residency Transfer request — collects EVERY
        missing item into one error rather than one-at-a-time discovery."""
        missing = [label for value, label in checks if not value]
        if missing:
            raise ValidationError(
                'Please complete the following before proceeding:\n- ' + '\n- '.join(missing)
            )

    def _notify_other_side(self, to_group, subject_suffix, extra=''):
        """Same pattern as the Residency Transfer request — HR actions
        notify GRO, GRO actions notify HR, symmetric at every stage."""
        self.ensure_one()
        from .field_pass_notifications import notify_track
        subject = f'Work Visa {self.name} — {subject_suffix}'
        body_html = (
            f'<p><b>{self.name}</b> — {self.candidate_name}</p>'
            f'<p>{subject_suffix}</p>'
        )
        if extra:
            body_html += f'<p>{extra}</p>'
        notify_track(self.env, to_group, subject, body_html)

    name = fields.Char(default='New', readonly=True, copy=False)

    # ── Candidate details — same structure as the Residency Transfer
    # request, confirmed ("all same above"), except Civil ID -> Passport No,
    # and Salary is present from the start rather than added at a later
    # stage (there's no two-stage Check/Transfer split here at all). ────────
    candidate_name = fields.Char(string='Candidate Name (English)', required=True)
    candidate_name_ar = fields.Char(string='اسم الموظف بالعربي')
    passport_no = fields.Char(string='Passport No - رقم الجواز', required=True)
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
    salary = fields.Float(string='Salary - الراتب')
    candidate_contact_no = fields.Char(string='Candidate Contact No - رقم اتصال المرشح')

    # ── Attachments — different set from the Residency Transfer request,
    # confirmed. ──────────────────────────────────────────────────────────
    attachment_passport = fields.Binary(string='Passport - جواز السفر', attachment=True)
    attachment_passport_name = fields.Char()
    attachment_education_degree = fields.Binary(string='Education Degree - الشهادة الدراسية', attachment=True)
    attachment_education_degree_name = fields.Char()
    attachment_job_offer = fields.Binary(string='Signed Job Offer - عرض العمل الموقع', attachment=True)
    attachment_job_offer_name = fields.Char()
    attachment_cv = fields.Binary(string='CV - السيرة الذاتية', attachment=True)
    attachment_cv_name = fields.Char()

    # ── Resolution ────────────────────────────────────────────────────────
    rejection_reason = fields.Text(string='Rejection Reason - سبب الرفض')
    attachment_issued_visa = fields.Binary(string='Issued Visa - سمة الدخول الصادرة', attachment=True)
    attachment_issued_visa_name = fields.Char()

    # ── Additional documents — ONLY relevant if HR chooses to keep the
    # request open after the visa is issued (confirmed branch). This chain
    # has 3 sub-stages, confirmed design: ────────────────────────────────────
    # 1) Awaiting Additional Documents — 6 uploads
    attachment_attested_education_cert = fields.Binary(string='Attested Education Certificate - شهادة مصدقة', attachment=True)
    attachment_attested_education_cert_name = fields.Char()
    attachment_education_transcript = fields.Binary(string='Education Transcript - كشف الدرجات', attachment=True)
    attachment_education_transcript_name = fields.Char()
    attachment_high_school_degree = fields.Binary(string='High School - شهادة الثانوية', attachment=True)
    attachment_high_school_degree_name = fields.Char()
    attachment_medical_checkup = fields.Binary(string='Medical Checkup Certificate - شهادة الفحص الطبي', attachment=True)
    attachment_medical_checkup_name = fields.Char()
    attachment_fingerprints = fields.Binary(string='Fingerprints - البصمات', attachment=True)
    attachment_fingerprints_name = fields.Char()
    attachment_no_criminal_record = fields.Binary(string='No Criminal Record Certificate - شهادة لا حكم عليه', attachment=True)
    attachment_no_criminal_record_name = fields.Char()

    # 2) Candidate Arrived — Degree Equivalency is a PROCESS step, no
    # upload (confirmed) — just a standing reminder note about the 3
    # education documents above needing to be attested/original. Ends
    # with the Work Permit copy, which IS required to proceed further
    # (confirmed: "without cannot go to next stage").
    degree_equivalency_note = fields.Text(
        string='Degree Equivalency Note - ملاحظة معادلة الشهادة',
        default=(
            'Original Attested Education Certificate, Education Transcript, and '
            'High School Degree — all attested and original copies needed.\n'
            'الشهادة الدراسية المصدقة الأصلية وكشف الدرجات وشهادة الثانوية '
            '— يجب أن تكون جميعها مصدقة ونسخ أصلية.'
        ),
    )
    attachment_work_permit_copy = fields.Binary(string='Work Permit Copy - نسخة إذن العمل', attachment=True)
    attachment_work_permit_copy_name = fields.Char()

    # 3) Issuing Civil ID — 3 uploads
    # ── New field, added specifically to support auto-creating an Employee
    # record on completion — Work Visa issues a BRAND NEW Civil ID, but
    # nothing previously captured its number as text (only a copy of the
    # card itself). ─────────────────────────────────────────────────────────
    civil_id_number = fields.Char(string='Civil ID Number - رقم البطاقة المدنية')
    attachment_blood_type = fields.Binary(string='Blood Type - فصيلة الدم', attachment=True)
    attachment_blood_type_name = fields.Char()
    attachment_personal_picture = fields.Binary(string='Personal Picture - صورة شخصية', attachment=True)
    attachment_personal_picture_name = fields.Char()
    attachment_rental_contract = fields.Binary(string='Rental Contract - عقد إيجار', attachment=True)
    attachment_rental_contract_name = fields.Char()

    # 4) Final closure documents (reused as-is — same fields already existed
    # for this purpose, confirmed same 3 documents: Health Insurance, MOI
    # Migration, Civil ID). ──────────────────────────────────────────────────
    attachment_health_insurance = fields.Binary(string='Health Insurance - الضمان الصحي', attachment=True)
    attachment_health_insurance_name = fields.Char()
    attachment_moi_migration = fields.Binary(string='MOI Migration - الهجرة', attachment=True)
    attachment_moi_migration_name = fields.Char()
    attachment_final_civil_id = fields.Binary(string='Civil ID - البطاقة المدنية', attachment=True)
    attachment_final_civil_id_name = fields.Char()

    state = fields.Selection([
        ('draft', 'Draft - مسودة'),
        ('submitted', 'Submitted - تم التقديم'),
        ('rejected', 'Rejected - مرفوض'),
        ('under_process', 'Under Process - قيد المعالجة'),
        ('completed', 'Completed - Visa Issued - مكتمل - تم إصدار السمة'),
        ('awaiting_additional_docs', 'Awaiting Additional Documents - بانتظار مستندات إضافية'),
        ('candidate_arrived', 'Candidate Arrived - وصول المرشح'),
        ('issuing_civil_id', 'Issuing Civil ID - إصدار البطاقة المدنية'),
        ('closed', 'Closed - مغلق'),
    ], default='draft', required=True, tracking=True)

    history_ids = fields.One2many(
        'field.pass.hr.visa.request.log', 'request_id', string='History - السجل')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'field.pass.hr.visa.request') or 'New'
        return super().create(vals_list)

    def _log(self, event_type, notes=''):
        self.ensure_one()
        self.env['field.pass.hr.visa.request.log'].create({
            'request_id': self.id,
            'event_type': event_type,
            'event_by': self.env.user.id,
            'notes': notes,
        })

    def action_submit(self):
        self.ensure_one()
        if self.state != 'draft':
            raise UserError('This request has already been submitted.')
        self._require([
            (self.candidate_name, 'Candidate Name (English)'),
            (self.candidate_name_ar, 'اسم الموظف بالعربي'),
            (self.passport_no, 'Passport No - رقم الجواز'),
            (self.company_id, 'Company - الشركة'),
            (self.department_id, 'Department - القسم'),
            (self.internal_position_title, 'Position Title - المسمى الوظيفي'),
            (self.suggested_position_title, 'Suggested Work Permit Position Title'),
            (self.salary, 'Salary - الراتب'),
            (self.candidate_contact_no, 'Candidate Contact No - رقم اتصال المرشح'),
            (self.attachment_passport, 'Passport - جواز السفر (upload)'),
            (self.attachment_education_degree, 'Education Degree - الشهادة الدراسية (upload)'),
            (self.attachment_job_offer, 'Signed Job Offer - عرض العمل الموقع (upload)'),
            (self.attachment_cv, 'CV - السيرة الذاتية (upload)'),
        ])
        self.state = 'submitted'
        self._log('submitted')
        self._notify_other_side('field_pass_tracker.group_fp_viewer', 'New Request Submitted')

    def action_open_reject_wizard(self):
        self.ensure_one()
        if self.state != 'submitted':
            raise UserError('Only a submitted request can be rejected.')
        return {
            'type': 'ir.actions.act_window',
            'name': 'Reject Request - رفض الطلب',
            'res_model': 'field.pass.hr.visa.reject.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_request_id': self.id},
        }

    def action_reject(self, reason):
        self.ensure_one()
        if self.state != 'submitted':
            raise UserError('Only a submitted request can be rejected.')
        self.write({'rejection_reason': reason, 'state': 'rejected'})
        self._log('rejected', notes=reason)
        self._notify_other_side('field_pass_tracker.group_fp_hr_viewer', 'Rejected', reason)

    def action_mark_under_process(self):
        self.ensure_one()
        if self.state != 'submitted':
            raise UserError('Only a submitted request can move to Under Process.')
        self.state = 'under_process'
        self._log('under_process')
        self._notify_other_side('field_pass_tracker.group_fp_hr_viewer', 'Under Process')

    def action_complete(self):
        """GRO uploads the issued visa. Confirmed: this does NOT close the
        request by itself — it lands in 'completed' with a follow-up
        decision (Close now / Keep Open) still to be made."""
        self.ensure_one()
        if self.state != 'under_process':
            raise UserError('Only a request Under Process can be marked Completed.')
        if not self.attachment_issued_visa:
            raise ValidationError('Please upload the Issued Visa before marking this Completed.')
        self.state = 'completed'
        self._log('completed')
        self._notify_other_side('field_pass_tracker.group_fp_hr_viewer', 'Visa Issued — Completed')

    def action_close_now(self):
        """Confirmed branch: close with ONLY the issued visa on file."""
        self.ensure_one()
        if self.state != 'completed':
            raise UserError('This request is not awaiting a close/keep-open decision.')
        self.state = 'closed'
        self._log('closed', notes='Closed with issued visa only — no additional documents.')
        self._notify_other_side('field_pass_tracker.group_fp_hr_viewer', 'Closed (Visa Only)')

    def action_keep_open(self):
        """Confirmed branch: keep going to collect the full document chain
        (education docs -> degree equivalency + work permit -> civil ID
        docs -> final closure) before final closure."""
        self.ensure_one()
        if self.state != 'completed':
            raise UserError('This request is not awaiting a close/keep-open decision.')
        self.state = 'awaiting_additional_docs'
        self._log('kept_open')
        self._notify_other_side('field_pass_tracker.group_fp_hr_viewer', 'Kept Open — Additional Documents Needed')

    def action_mark_candidate_arrived(self):
        """
        Confirmed design update: the 6 documents from the Awaiting
        Additional Documents stage are now required here — previously this
        transition had no requirement at all, but per the general "block
        every stage until its data is complete" rule, this was a real gap.
        Degree Equivalency itself is still process-only (no upload needed
        for that specific item).
        """
        self.ensure_one()
        if self.state != 'awaiting_additional_docs':
            raise UserError('This request is not awaiting the candidate to arrive.')
        self._require([
            (self.attachment_attested_education_cert, 'Attested Education Certificate - شهادة مصدقة (upload)'),
            (self.attachment_education_transcript, 'Education Transcript - كشف الدرجات (upload)'),
            (self.attachment_high_school_degree, 'High School - شهادة الثانوية (upload)'),
            (self.attachment_medical_checkup, 'Medical Checkup Certificate - شهادة الفحص الطبي (upload)'),
            (self.attachment_fingerprints, 'Fingerprints - البصمات (upload)'),
            (self.attachment_no_criminal_record, 'No Criminal Record Certificate - شهادة لا حكم عليه (upload)'),
        ])
        self.state = 'candidate_arrived'
        self._log('candidate_arrived')
        self._notify_other_side('field_pass_tracker.group_fp_hr_viewer', 'Candidate Arrived')

    def action_issue_work_permit(self):
        """Confirmed hard requirement: cannot proceed without the Work
        Permit copy uploaded."""
        self.ensure_one()
        if self.state != 'candidate_arrived':
            raise UserError('This request is not at the Candidate Arrived stage.')
        if not self.attachment_work_permit_copy:
            raise ValidationError('Please upload the Work Permit copy before proceeding.')
        self.state = 'issuing_civil_id'
        self._log('work_permit_issued')
        self._notify_other_side('field_pass_tracker.group_fp_hr_viewer', 'Work Permit Issued')

    def action_finalize(self):
        self.ensure_one()
        if self.state != 'issuing_civil_id':
            raise UserError('This request is not awaiting final closure.')
        self._require([
            (self.civil_id_number, 'Civil ID Number - رقم البطاقة المدنية'),
            (self.attachment_blood_type, 'Blood Type - فصيلة الدم (upload)'),
            (self.attachment_personal_picture, 'Personal Picture - صورة شخصية (upload)'),
            (self.attachment_rental_contract, 'Rental Contract - عقد إيجار (upload)'),
            (self.attachment_health_insurance, 'Health Insurance - الضمان الصحي (upload)'),
            (self.attachment_moi_migration, 'MOI Migration - الهجرة (upload)'),
            (self.attachment_final_civil_id, 'Civil ID - البطاقة المدنية (upload)'),
        ])
        self.state = 'closed'
        self._log('closed', notes='Closed with full additional-document chain completed.')
        self._notify_other_side('field_pass_tracker.group_fp_hr_viewer', 'Finalized — Closed')
        self._create_employee_record()

    def _create_employee_record(self):
        """
        Confirmed design: ONLY the full chain (through Issuing Civil ID ->
        Finalize) creates an Employee record — deliberately NOT
        action_close_now(), since that path never issues a Civil ID at all
        ("new work visa AND new civil ID" was the confirmed trigger
        condition). HR Request stays a one-time onboarding record; Employee
        becomes the ongoing source of truth from here on.

        Same field-sharing philosophy as the Residency Transfer request —
        only genuinely shared fields copied, Company left at Employee's own
        default (different model than this request's Company field).
        """
        self.ensure_one()
        Employee = self.env['field.pass.employee']
        vals = {
            'name': self.candidate_name,
            'name_ar': self.candidate_name_ar,
            'department_id': self.department_id.id,
            'designation': self.internal_position_title,
        }
        if self.attachment_final_civil_id:
            vals['attachment_civil_id'] = self.attachment_final_civil_id
            vals['attachment_civil_id_name'] = self.attachment_final_civil_id_name
        if self.attachment_passport:
            vals['attachment_passport'] = self.attachment_passport
            vals['attachment_passport_name'] = self.attachment_passport_name
        employee = Employee.create(vals)
        self._log('employee_created', notes=f'Employee record created: {employee.name} (#{employee.id})')

    def action_reopen(self):
        """Same design as the Residency Transfer request — Rejected is not
        a permanent dead end."""
        self.ensure_one()
        if self.state != 'rejected':
            raise UserError('Only a rejected request can be reopened.')
        old_reason = self.rejection_reason
        self.write({'rejection_reason': False, 'state': 'submitted'})
        self._log('reopened', notes=f'Previous rejection reason: {old_reason}')
        self._notify_other_side('field_pass_tracker.group_fp_viewer', 'Reopened')


class FieldPassHrVisaRequestLog(models.Model):
    _name = 'field.pass.hr.visa.request.log'
    _description = 'Work Visa Request — Event Log'
    _order = 'event_date desc'

    request_id = fields.Many2one(
        'field.pass.hr.visa.request', required=True, ondelete='cascade', index=True)
    event_type = fields.Selection([
        ('submitted', 'Submitted'),
        ('rejected', 'Rejected'),
        ('reopened', 'Reopened'),
        ('under_process', 'Under Process'),
        ('completed', 'Completed'),
        ('kept_open', 'Kept Open'),
        ('candidate_arrived', 'Candidate Arrived'),
        ('work_permit_issued', 'Work Permit Issued'),
        ('closed', 'Closed'),
        ('employee_created', 'Employee Record Created'),
    ], required=True)
    event_date = fields.Datetime(default=fields.Datetime.now, required=True)
    event_by = fields.Many2one('res.users', default=lambda self: self.env.user, required=True)
    notes = fields.Text()


class FieldPassHrVisaRejectWizard(models.TransientModel):
    _name = 'field.pass.hr.visa.reject.wizard'
    _description = 'Reject — Work Visa Request'

    request_id = fields.Many2one('field.pass.hr.visa.request', required=True)
    reason = fields.Text(string='Rejection Reason - سبب الرفض', required=True)

    def action_confirm(self):
        self.ensure_one()
        self.request_id.action_reject(self.reason)
        return {'type': 'ir.actions.act_window_close'}
