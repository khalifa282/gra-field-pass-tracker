# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import date


class FieldPassEmployee(models.Model):
    _name = 'field.pass.employee'
    _description = 'Field Pass Employee'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'department_id, name'
    _rec_name = 'name'

    # ── Identity ──────────────────────────────────────────────────────────────
    name = fields.Char(string='Employee Name', required=True, tracking=True)
    name_ar = fields.Char(string='Arabic Name - الاسم بالعربي', tracking=True)
    employee_number = fields.Char(string='Employee Number', tracking=True)
    nationality = fields.Char(string='Nationality', tracking=True)
    designation = fields.Char(string='Designation', tracking=True)
    job_type = fields.Selection(
        [('Field', 'Field'), ('Office', 'Office'), ('Driver', 'Driver')],
        string='Job Type', required=True, default='Field', tracking=True,
    )
    gcc_national = fields.Boolean(string='GCC National', default=False, tracking=True)
    active = fields.Boolean(default=True, tracking=True)
    company_id = fields.Many2one(
        'res.company', required=True,
        default=lambda self: self.env.company, tracking=True,
    )
    department_id = fields.Many2one(
        'hr.department', string='Department', required=True,
        tracking=True, ondelete='restrict',
    )
    contract_id = fields.Many2one(
        'field.pass.contract', string='Contract', tracking=True,
        domain="[('department_id','=',department_id),('active','=',True)]",
    )
    remarks = fields.Text(string='Remarks', tracking=True)

    # ── Department client flags ────────────────────────────────────────────────
    dept_has_koc = fields.Boolean(compute='_compute_dept_clients', store=False)
    dept_has_wjo = fields.Boolean(compute='_compute_dept_clients', store=False)

    allowed_pass_types = fields.Char(compute='_compute_allowed_pass_types', store=False)

    @api.depends('department_id.fp_client_koc', 'department_id.fp_client_wjo')
    def _compute_allowed_pass_types(self):
        for e in self:
            types = ['TEMP']
            if e.department_id and e.department_id.fp_client_koc:
                types += ['KOC', 'RATQA_ABDALLY']
            if e.department_id and e.department_id.fp_client_wjo:
                types += ['WAFRA', 'FAWARES']
            e.allowed_pass_types = ','.join(types)

    @api.depends('department_id', 'department_id.fp_client_koc', 'department_id.fp_client_wjo')
    def _compute_dept_clients(self):
        for e in self:
            e.dept_has_koc = e.department_id.fp_client_koc if e.department_id else False
            e.dept_has_wjo = e.department_id.fp_client_wjo if e.department_id else False

    # ── CV Approval (KOC client) ───────────────────────────────────────────────
    cv_approval_status = fields.Selection(
        [('not_approved', 'Not Approved'), ('under_process', 'Under Process'),
         ('cv_approved', 'CV Approved'), ('exempted', 'Exempted')],
        string='CV Approval', default='not_approved', tracking=True,
    )
    attachment_cv_approval = fields.Binary(string='CV Approval Document', attachment=True)
    attachment_cv_approval_name = fields.Char()

    # ── WJO HSE Training ──────────────────────────────────────────────────────
    wjo_hse_training_attended = fields.Boolean(
        string='WJO HSE Training Attended', default=False, tracking=True,
    )
    attachment_wjo_hse = fields.Binary(string='WJO HSE Certificate', attachment=True)
    attachment_wjo_hse_name = fields.Char()

    # ── GOVERNMENT DOCUMENTS ──────────────────────────────────────────────────
    passport_validity = fields.Date(string='Passport Validity', tracking=True)
    passport_status = fields.Selection(
        [('valid','Valid'),('warning','Warning'),('expired','Expired'),('na','Not Required')],
        compute='_compute_statuses', store=True,
    )
    passport_days = fields.Integer(compute='_compute_statuses', store=True)
    attachment_passport = fields.Binary(string='Passport Document', attachment=True)
    attachment_passport_name = fields.Char()

    residency_validity = fields.Date(string='Residency Validity', tracking=True)
    residency_status = fields.Selection(
        [('valid','Valid'),('warning','Warning'),('expired','Expired'),('na','Not Required')],
        compute='_compute_statuses', store=True,
    )
    residency_days = fields.Integer(compute='_compute_statuses', store=True)
    attachment_residency = fields.Binary(string='Residency Document', attachment=True)
    attachment_residency_name = fields.Char()

    civil_id_number = fields.Char(string='Civil ID Number', tracking=True)
    civil_id_validity = fields.Date(string='Civil ID Validity', tracking=True)
    civil_id_status = fields.Selection(
        [('valid','Valid'),('warning','Warning'),('expired','Expired'),('na','Not Required')],
        compute='_compute_statuses', store=True,
    )
    civil_id_days = fields.Integer(compute='_compute_statuses', store=True)
    attachment_civil_id = fields.Binary(string='Civil ID Document', attachment=True)
    attachment_civil_id_name = fields.Char()

    track_driving_license = fields.Boolean(
        string='Track Driving License', default=False, tracking=True,
    )
    driving_license_validity = fields.Date(string='Driving License Validity', tracking=True)
    driving_license_status = fields.Selection(
        [('valid','Valid'),('warning','Warning'),('expired','Expired'),('na','Not Required')],
        compute='_compute_statuses', store=True,
    )
    driving_license_days = fields.Integer(compute='_compute_statuses', store=True)
    attachment_driving_license = fields.Binary(string='Driving License Document', attachment=True)
    attachment_driving_license_name = fields.Char()

    # ── DRIVER DOCUMENTS ──────────────────────────────────────────────────────
    driving_authority_validity = fields.Date(string='Driving Authority Validity', tracking=True)
    driving_authority_status = fields.Selection(
        [('valid','Valid'),('warning','Warning'),('expired','Expired'),('na','Not Required')],
        compute='_compute_statuses', store=True,
    )
    attachment_driving_authority = fields.Binary(string='Driving Authority Document', attachment=True)
    attachment_driving_authority_name = fields.Char()

    driving_hse_training_date = fields.Date(
        string='Driving HSE Training Date', tracking=True,
        help="Date training was completed. Once set, status is 'Valid' unless an expiry date below is also set.",
    )
    driving_hse_expiry_date = fields.Date(
        string='Driving HSE Training Expiry (optional)', tracking=True,
        help="Optional. If set, training will show as expiring/expired based on this date. "
             "If left blank, training is valid indefinitely once completed.",
    )
    driving_hse_status = fields.Selection(
        [('valid','Valid'),('warning','Warning'),('expired','Expired'),('na','Not Required')],
        compute='_compute_statuses', store=True,
    )
    attachment_driving_hse = fields.Binary(string='Driving HSE Certificate', attachment=True)
    attachment_driving_hse_name = fields.Char()

    # NOTE: PTW and KOC Laptop Pass moved to Pass Application/Renewal
    # (field.pass model, pass_type='PTW'/'KOC_LAPTOP') -- confirmed change,
    # no longer tracked as Employee document fields. See field_pass.py.

    # ── Overall document status ────────────────────────────────────────────────
    overall_doc_status = fields.Selection(
        [('valid','Valid'),('warning','Warning'),('expired','Expired')],
        compute='_compute_overall_doc', store=True,
    )

    # ── Field Passes ──────────────────────────────────────────────────────────
    pass_ids = fields.One2many('field.pass', 'employee_id', string='Field Passes')
    pass_count = fields.Integer(compute='_compute_pass_count')

    pass_koc_status = fields.Selection(
        [('valid','Valid'),('warning','Expiring Soon'),('expired','Expired'),
         ('temp_active','Temp Active'),('temp_warning','Temp Expiring'),
         ('missing','No Expiry Date - لا يوجد تاريخ'),('not_required','Not Required')],
        compute='_compute_pass_statuses', store=True,
    )
    pass_ratqa_status = fields.Selection(
        [('valid','Valid'),('warning','Expiring Soon'),('expired','Expired'),
         ('temp_active','Temp Active'),('temp_warning','Temp Expiring'),
         ('missing','No Expiry Date - لا يوجد تاريخ'),('not_required','Not Required')],
        compute='_compute_pass_statuses', store=True,
    )
    pass_wafra_status = fields.Selection(
        [('valid','Valid'),('warning','Expiring Soon'),('expired','Expired'),
         ('temp_active','Temp Active'),('temp_warning','Temp Expiring'),
         ('missing','No Expiry Date - لا يوجد تاريخ'),('not_required','Not Required')],
        compute='_compute_pass_statuses', store=True,
    )
    pass_fawares_status = fields.Selection(
        [('valid','Valid'),('warning','Expiring Soon'),('expired','Expired'),
         ('temp_active','Temp Active'),('temp_warning','Temp Expiring'),
         ('missing','No Expiry Date - لا يوجد تاريخ'),('not_required','Not Required')],
        compute='_compute_pass_statuses', store=True,
    )

    overall_status = fields.Selection(
        [('valid','Valid'),('warning','Warning'),
         ('expired','Expired'),('missing','Missing Pass')],
        compute='_compute_overall', store=True, string='Overall Status',
    )

    # ── History tabs ──────────────────────────────────────────────────────────
    renewal_history_ids = fields.One2many(
        'field.pass.renewal', 'employee_id',
        string='Document Renewal History', readonly=True)
    pass_app_history_ids = fields.One2many(
        'field.pass.application', 'employee_id',
        string='Field Pass History', readonly=True)

    # ── Summary Tab ───────────────────────────────────────────────────────────
    def _get_validity_status(self, expiry_field, warn_days=30):
        from datetime import date as dt
        expiry = getattr(self, expiry_field, False)
        if not expiry:
            return 'missing'
        delta = (expiry - dt.today()).days
        if delta < 0:
            return 'expired'
        elif delta <= warn_days:
            return 'warning'
        return 'valid'

    def _get_renewal_status(self, doc_type):
        latest = self.env['field.pass.renewal'].sudo().search([
            ('employee_id', '=', self.id),
            ('document_type', '=', doc_type),
        ], order='event_date desc', limit=1)
        if not latest:
            return 'none'
        return latest.event_type

    def _get_pass_validity(self, pass_type):
        from datetime import date as dt
        rec = self.env['field.pass'].sudo().search([
            ('employee_id', '=', self.id),
            ('pass_type', '=', pass_type),
            ('is_temp', '=', False),
        ], limit=1)
        if not rec or not rec.date_expire:
            return 'missing'
        delta = (rec.date_expire - dt.today()).days
        if delta < 0:
            return 'expired'
        elif delta <= 30:
            return 'warning'
        return 'valid'

    def _get_app_status(self, pass_type):
        latest = self.env['field.pass.application'].sudo().search([
            ('employee_id', '=', self.id),
            ('pass_type', '=', pass_type),
        ], order='event_date desc', limit=1)
        if not latest:
            return 'none'
        return latest.state

    @api.depends('passport_validity', 'residency_validity', 'civil_id_validity',
                 'driving_license_validity',
                 'driving_hse_training_date', 'driving_authority_validity',
                 'renewal_history_ids', 'pass_app_history_ids')
    def _compute_summary_v2(self):
        for r in self:
            r.sv_passport = r._get_validity_status('passport_validity')
            r.sv_residency = r._get_validity_status('residency_validity')
            r.sv_civil_id = r._get_validity_status('civil_id_validity')
            r.sv_driving_license = r._get_validity_status('driving_license_validity')
            r.sv_driving_hse = r._get_validity_status('driving_hse_training_date')
            r.sv_driving_authority = r._get_validity_status('driving_authority_validity')
            r.sa_passport = r._get_renewal_status('passport')
            r.sa_residency = r._get_renewal_status('residency')
            r.sa_civil_id = r._get_renewal_status('civil_id')
            r.sa_driving_license = r._get_renewal_status('driving_license')
            r.sa_driving_hse = r._get_renewal_status('driving_hse')
            r.sa_driving_authority = r._get_renewal_status('driving_authority')
            r.sv_koc_pass = r._get_pass_validity('KOC')
            r.sv_ratqa_pass = r._get_pass_validity('RATQA_ABDALLY')
            r.sv_wafra_pass = r._get_pass_validity('WAFRA')
            r.sv_fawares_pass = r._get_pass_validity('FAWARES')
            r.sv_temp_pass = r._get_pass_validity('TEMP')
            # MOVED: PTW and KOC Laptop Pass are now Pass Application/Renewal
            # types (like KOC/RATQA/WAFRA), not Document Renewal fields.
            r.sv_ptw_pass = r._get_pass_validity('PTW')
            r.sv_koc_laptop_pass = r._get_pass_validity('KOC_LAPTOP')
            r.sa_koc_pass = r._get_app_status('KOC')
            r.sa_ratqa_pass = r._get_app_status('RATQA_ABDALLY')
            r.sa_wafra_pass = r._get_app_status('WAFRA')
            r.sa_fawares_pass = r._get_app_status('FAWARES')
            r.sa_temp_pass = r._get_app_status('TEMP')
            r.sa_ptw_pass = r._get_app_status('PTW')
            r.sa_koc_laptop_pass = r._get_app_status('KOC_LAPTOP')

    _VALIDITY = [('valid','Valid - صالح'),('warning','Expiring Soon - ينتهي قريباً'),
                 ('expired','Expired - منتهي'),('missing','No Expiry Date - لا يوجد تاريخ')]
    _APP_STATUS = [('none','—'),('submitted','Submitted - مقدم'),
                   ('rejected','Rejected - مرفوض'),('issued','Issued - صادر')]

    sv_passport = fields.Selection(_VALIDITY, compute='_compute_summary_v2', string='Validity')
    sv_residency = fields.Selection(_VALIDITY, compute='_compute_summary_v2', string='Validity')
    sv_civil_id = fields.Selection(_VALIDITY, compute='_compute_summary_v2', string='Validity')
    sv_driving_license = fields.Selection(_VALIDITY, compute='_compute_summary_v2', string='Validity')
    sv_driving_hse = fields.Selection(_VALIDITY, compute='_compute_summary_v2', string='Validity')
    sv_driving_authority = fields.Selection(_VALIDITY, compute='_compute_summary_v2', string='Validity')
    sv_koc_pass = fields.Selection(_VALIDITY, compute='_compute_summary_v2', string='Validity')
    sv_ratqa_pass = fields.Selection(_VALIDITY, compute='_compute_summary_v2', string='Validity')
    sv_wafra_pass = fields.Selection(_VALIDITY, compute='_compute_summary_v2', string='Validity')
    sv_fawares_pass = fields.Selection(_VALIDITY, compute='_compute_summary_v2', string='Validity')
    sv_temp_pass = fields.Selection(_VALIDITY, compute='_compute_summary_v2', string='Validity')
    sv_ptw_pass = fields.Selection(_VALIDITY, compute='_compute_summary_v2', string='Validity')
    sv_koc_laptop_pass = fields.Selection(_VALIDITY, compute='_compute_summary_v2', string='Validity')
    sa_passport = fields.Selection(_APP_STATUS, compute='_compute_summary_v2', string='Application Status')
    sa_residency = fields.Selection(_APP_STATUS, compute='_compute_summary_v2', string='Application Status')
    sa_civil_id = fields.Selection(_APP_STATUS, compute='_compute_summary_v2', string='Application Status')
    sa_driving_license = fields.Selection(_APP_STATUS, compute='_compute_summary_v2', string='Application Status')
    sa_driving_hse = fields.Selection(_APP_STATUS, compute='_compute_summary_v2', string='Application Status')
    sa_driving_authority = fields.Selection(_APP_STATUS, compute='_compute_summary_v2', string='Application Status')
    sa_koc_pass = fields.Selection(_APP_STATUS, compute='_compute_summary_v2', string='Application Status')
    sa_ratqa_pass = fields.Selection(_APP_STATUS, compute='_compute_summary_v2', string='Application Status')
    sa_wafra_pass = fields.Selection(_APP_STATUS, compute='_compute_summary_v2', string='Application Status')
    sa_fawares_pass = fields.Selection(_APP_STATUS, compute='_compute_summary_v2', string='Application Status')
    sa_temp_pass = fields.Selection(_APP_STATUS, compute='_compute_summary_v2', string='Application Status')
    sa_ptw_pass = fields.Selection(_APP_STATUS, compute='_compute_summary_v2', string='Application Status')
    sa_koc_laptop_pass = fields.Selection(_APP_STATUS, compute='_compute_summary_v2', string='Application Status')

    # ── Helpers ───────────────────────────────────────────────────────────────
    def _warn(self, doc_type):
        return self.env['field.pass.alert.config'].get_warn_days(
            doc_type, self.company_id.id or self.env.company.id)

    def _calc(self, expiry_date, warn_days):
        if not expiry_date:
            return 'na', 0
        delta = (expiry_date - date.today()).days
        if delta < 0:
            return 'expired', delta
        if delta <= warn_days:
            return 'warning', delta
        return 'valid', delta

    def _calc_pass_status(self, pass_type, required, warn_days):
        if not required:
            return 'not_required'
        main = self.sudo().pass_ids.filtered(lambda p: p.pass_type == pass_type and not p.is_temp)
        temp = self.sudo().pass_ids.filtered(lambda p: p.pass_type == 'TEMP' and p.is_temp)
        if not main:
            if temp and temp[0].date_expire:
                delta = (temp[0].date_expire - date.today()).days
                if delta < 0:
                    return 'missing'
                return 'temp_warning' if delta <= warn_days else 'temp_active'
            return 'missing'
        if not main[0].date_expire:
            return 'missing'
        delta = (main[0].date_expire - date.today()).days
        if delta >= 0:
            return 'warning' if delta <= warn_days else 'valid'
        if temp and temp[0].date_expire:
            temp_delta = (temp[0].date_expire - date.today()).days
            if temp_delta >= 0:
                return 'temp_warning' if temp_delta <= warn_days else 'temp_active'
        return 'expired'

    # ── Computes ──────────────────────────────────────────────────────────────
    @api.depends(
        'passport_validity', 'residency_validity', 'gcc_national',
        'civil_id_validity', 'driving_license_validity', 'track_driving_license',
        'job_type', 'driving_authority_validity', 'driving_hse_training_date',
        'driving_hse_expiry_date',
        'company_id',
    )
    def _compute_statuses(self):
        for e in self:
            e.passport_status, e.passport_days = e._calc(e.passport_validity, e._warn('passport'))
            if e.gcc_national:
                e.residency_status, e.residency_days = 'na', 0
            else:
                e.residency_status, e.residency_days = e._calc(e.residency_validity, e._warn('residency'))
            e.civil_id_status, e.civil_id_days = e._calc(e.civil_id_validity, e._warn('civil_id'))
            if e.job_type == 'Driver' or e.track_driving_license:
                e.driving_license_status, e.driving_license_days = e._calc(
                    e.driving_license_validity, e._warn('driving_license'))
            else:
                e.driving_license_status, e.driving_license_days = 'na', 0
            if e.job_type == 'Driver':
                e.driving_authority_status, _ = e._calc(e.driving_authority_validity, e._warn('driving_authority'))
                # FIX: previously ran driving_hse_training_date through the
                # same expiry-style calculation as everything else -- since
                # a training COMPLETION date is always in the past, this
                # made driving_hse_status show 'expired' forever, for every
                # driver, regardless of how recently they trained. Now:
                # "once obtained is valid", with the new optional
                # driving_hse_expiry_date overriding this with a real
                # valid/warning/expired calculation if the company wants to
                # track a specific renewal deadline.
                if e.driving_hse_expiry_date:
                    e.driving_hse_status, _ = e._calc(e.driving_hse_expiry_date, e._warn('driving_hse'))
                elif e.driving_hse_training_date:
                    e.driving_hse_status = 'valid'
                else:
                    e.driving_hse_status = 'na'
            else:
                e.driving_authority_status = 'na'
                e.driving_hse_status = 'na'
            # NOTE: PTW and KOC Laptop Pass status no longer computed here --
            # moved to field.pass (pass_type='PTW'/'KOC_LAPTOP'), tracked via
            # the Pass Application/Renewal workflow instead.

    @api.depends(
        'passport_status', 'residency_status', 'civil_id_status',
        'driving_license_status', 'driving_authority_status', 'driving_hse_status',
    )
    def _compute_overall_doc(self):
        RANK = {'expired': 2, 'warning': 1, 'valid': 0, 'na': -1}
        FIELDS = ['passport_status', 'residency_status', 'civil_id_status',
                  'driving_license_status', 'driving_authority_status',
                  'driving_hse_status']
        for e in self:
            worst = max(RANK.get(getattr(e, f, 'na'), -1) for f in FIELDS)
            e.overall_doc_status = ('expired' if worst == 2 else
                                    'warning' if worst == 1 else 'valid')

    @api.depends(
        'pass_ids', 'pass_ids.pass_type', 'pass_ids.date_expire', 'pass_ids.is_temp',
        'department_id', 'department_id.fp_client_koc', 'department_id.fp_client_wjo',
    )
    def _compute_pass_statuses(self):
        for e in self:
            dept = e.department_id
            koc = dept.fp_client_koc if dept else False
            wjo = dept.fp_client_wjo if dept else False
            warn = e._warn('fp_koc')
            e.pass_koc_status    = e._calc_pass_status('KOC', koc, warn)
            e.pass_ratqa_status  = e._calc_pass_status('RATQA_ABDALLY', koc, warn)
            e.pass_wafra_status  = e._calc_pass_status('WAFRA', wjo, warn)
            e.pass_fawares_status = e._calc_pass_status('FAWARES', wjo, warn)

    @api.depends('overall_doc_status', 'pass_koc_status', 'pass_ratqa_status',
                 'pass_wafra_status', 'pass_fawares_status')
    def _compute_overall(self):
        RANK = {'expired': 3, 'missing': 3, 'temp_warning': 2, 'warning': 2,
                'temp_active': 1, 'valid': 0, 'not_required': -1, 'na': -1}
        PASS_FIELDS = ['pass_koc_status', 'pass_ratqa_status',
                       'pass_wafra_status', 'pass_fawares_status']
        for e in self:
            doc_rank = RANK.get(e.overall_doc_status, 0)
            pass_rank = max(RANK.get(getattr(e, f, 'not_required'), -1) for f in PASS_FIELDS)
            worst = max(doc_rank, pass_rank)
            if worst >= 3:
                e.overall_status = 'expired' if doc_rank >= 3 else 'missing'
            elif worst == 2:
                e.overall_status = 'warning'
            else:
                e.overall_status = 'valid'

    def _compute_pass_count(self):
        for e in self:
            e.pass_count = len(e.sudo().pass_ids)



    @api.onchange('driving_authority_validity')
    def _onchange_driving_authority(self):
        if self.driving_authority_validity and not self.driving_hse_training_date:
            self.driving_authority_validity = False
            return {'warning': {
                'title': 'Prerequisite Missing - متطلب مفقود',
                'message': 'Driving HSE Training must be completed before setting Driving Authority.'
            }}

    # NOTE: the old _onchange_ptw method was removed here -- track_ptw/
    # ptw_expiry_date no longer exist on Employee (moved to Pass
    # Application/Renewal). The same "valid KOC pass required" check now
    # lives in field_pass.py's _check_documents_ready and the Application
    # wizard's action_submit_application.

    # ── Prerequisites ─────────────────────────────────────────────────────────
    # Domino chain, confirmed design: each document blocked from being set
    # unless the PREVIOUS document in the chain is currently valid (valid or
    # warning status both count — only expired/missing blocks).
    #   Chain A: Passport -> Residency -> Civil ID (GCC skips Residency)
    #   Chain B: Civil ID -> Driving License -> Driving HSE -> Driving Authority
    _OK_STATUSES = ('valid', 'warning')

    # ── Domino chain prerequisite checks ─────────────────────────────────────
    # BUG FIX (confirmed via real report: renewing Passport threw "Cannot set
    # Civil ID... Residency must be valid first"): these constraints were
    # decorated to also re-fire whenever a DOWNSTREAM status changed (e.g.
    # civil_id's check also listed passport_status/residency_status as
    # triggers). Since @api.constrains fires on ANY listed dependency
    # changing — not just the field the constraint is actually about —
    # simply renewing an EARLIER document (recomputing its status) was
    # retroactively re-validating LATER documents nobody touched, and
    # blocking the very renewal meant to fix the chain. Each constraint now
    # only re-checks when its OWN date field (or a genuinely relevant
    # trigger like nationality/job type) changes — not when a downstream
    # status recomputes as a side effect.
    @api.constrains('residency_validity', 'gcc_national')
    def _check_residency_prerequisite(self):
        for e in self:
            if e.residency_validity and not e.gcc_national:
                if e.passport_status not in e._OK_STATUSES:
                    raise ValidationError(
                        f'Cannot set Residency for "{e.name}": Passport must be valid first.'
                    )

    @api.constrains('civil_id_validity', 'gcc_national')
    def _check_civil_id_prerequisite(self):
        for e in self:
            if not e.civil_id_validity:
                continue
            if e.gcc_national:
                if e.passport_status not in e._OK_STATUSES:
                    raise ValidationError(
                        f'Cannot set Civil ID for "{e.name}": Passport must be valid first.'
                    )
            else:
                if e.residency_status not in e._OK_STATUSES:
                    raise ValidationError(
                        f'Cannot set Civil ID for "{e.name}": Residency must be valid first.'
                    )

    @api.constrains('driving_license_validity')
    def _check_driving_license_prerequisite(self):
        for e in self:
            if e.driving_license_validity and e.civil_id_status not in e._OK_STATUSES:
                raise ValidationError(
                    f'Cannot set Driving License for "{e.name}": Civil ID must be valid first.'
                )

    @api.constrains('driving_hse_training_date', 'job_type')
    def _check_driving_hse_prerequisite(self):
        for e in self:
            if e.driving_hse_training_date and e.job_type == 'Driver':
                if e.driving_license_status not in e._OK_STATUSES:
                    raise ValidationError(
                        f'Cannot record Driving HSE Training for "{e.name}": '
                        f'Driving License must be valid first.'
                    )

    @api.constrains('driving_authority_validity')
    def _check_driving_authority_prerequisite(self):
        # UPGRADED: previously only checked whether driving_hse_training_date
        # was SET at all (regardless of whether it was actually valid). Now
        # checks the live driving_hse_status, consistent with the rest of
        # the domino chain -- an expired HSE (per the optional expiry date)
        # now correctly blocks Driving Authority too, not just a missing one.
        for e in self:
            if e.driving_authority_validity and e.driving_hse_status not in e._OK_STATUSES:
                raise ValidationError(
                    f'Cannot set Driving Authority for "{e.name}". '
                    f'Driving HSE Training must be valid first.'
                )

    # NOTE: _check_ptw_prerequisite and _check_koc_laptop_prerequisite were
    # removed here -- those fields no longer exist on Employee. The "valid
    # KOC pass required" rule now lives on field.pass itself and the
    # Application wizard, applied uniformly to all pass types that need it.


    def _get_app_status_label(self, pass_type):
        latest = self.env['field.pass.application'].sudo().search([
            ('employee_id', '=', self.id),
            ('pass_type', '=', pass_type),
        ], order='event_date desc', limit=1)
        if not latest or latest.state == 'none':
            return ''
        date_str = latest.event_date.strftime('%d/%m/%Y') if latest.event_date else ''
        state_label = {'submitted': 'Submitted', 'rejected': 'Rejected', 'issued': 'Issued'}.get(latest.state, '')
        return f'{state_label} - {date_str}' if date_str else state_label

    @api.depends('pass_app_history_ids')
    def _compute_app_labels(self):
        for r in self:
            r.sa_koc_pass_label     = r._get_app_status_label('KOC')
            r.sa_ratqa_pass_label   = r._get_app_status_label('RATQA_ABDALLY')
            r.sa_wafra_pass_label   = r._get_app_status_label('WAFRA')
            r.sa_fawares_pass_label = r._get_app_status_label('FAWARES')
            r.sa_temp_pass_label    = r._get_app_status_label('TEMP')

    sa_koc_pass_label     = fields.Char(compute='_compute_app_labels', string='KOC Application')
    sa_ratqa_pass_label   = fields.Char(compute='_compute_app_labels', string='RATQA Application')
    sa_wafra_pass_label   = fields.Char(compute='_compute_app_labels', string='Wafra Application')
    sa_fawares_pass_label = fields.Char(compute='_compute_app_labels', string='Fawares Application')
    sa_temp_pass_label    = fields.Char(compute='_compute_app_labels', string='Temp Application')

    def action_view_passes(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Field Passes — {self.name}',
            'res_model': 'field.pass',
            'view_mode': 'tree,form',
            'domain': [('employee_id', '=', self.id)],
            'context': {'default_employee_id': self.id},
        }
