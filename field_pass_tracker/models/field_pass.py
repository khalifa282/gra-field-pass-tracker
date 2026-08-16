# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import date


PASS_TYPES = [
    # NOTE: this list is duplicated in 3 places with no single source of
    # truth — field_pass.py (here), field_pass_application.py, and
    # field_pass_renewal_wizard.py. This is a pre-existing design fragility,
    # not something introduced by this change. When adding/changing a pass
    # type, all 3 copies must be updated together (confirmed the hard way —
    # missing field_pass_application.py's copy caused a runtime error).
    ('KOC',           'KOC Field Pass'),
    ('RATQA_ABDALLY', 'RATQA & Abdally GP'),
    ('WAFRA',         'Wafra Field Pass'),
    ('FAWARES',       'Fawares Field Pass'),
    ('TEMP',          'Temp Field Pass'),
    # MOVED from Employee document fields to real Pass records — confirmed
    # change. Employee-only (no vehicle equivalent).
    ('PTW',           'PTW'),
    ('KOC_LAPTOP',    'KOC Laptop Pass'),
]

APP_STATUS = [
    ('no',            'No Application'),
    ('under_process', 'Under Process'),
    ('yes',           'Active / Issued'),
]

DOC_KEY_MAP = {
    'KOC': 'fp_koc', 'RATQA_ABDALLY': 'fp_ratqa_abdally',
    'WAFRA': 'fp_wafra', 'FAWARES': 'fp_fawares', 'TEMP': 'fp_temp',
    # Reuses the SAME AlertConfig document_type keys ('ptw'/'koc_laptop')
    # that were already configured back when these were Employee fields —
    # the warning-threshold settings carry over unchanged.
    'PTW': 'ptw', 'KOC_LAPTOP': 'koc_laptop',
}

# Maps department requirement field -> pass type
DEPT_REQUIRE_MAP = {
    'fp_require_koc':     'KOC',
    'fp_require_ratqa':   'RATQA_ABDALLY',
    'fp_require_wafra':   'WAFRA',
    'fp_require_fawares': 'FAWARES',
}

EXPIRY_STATUS = [
    ('valid',        'Valid'),
    ('warning',      'Expiring Soon'),
    ('expired',      'Expired'),
    ('temp_active',  'Temp Pass Active'),
    ('temp_warning', 'Temp Pass Expiring'),
    ('missing',      'Missing'),
    ('not_required', 'Not Required'),
    ('na',           'No Date'),
]


class FieldPass(models.Model):
    _name = 'field.pass'
    _description = 'Field Pass'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_expire asc, pass_type asc'
    _rec_name = 'display_name'

    employee_id = fields.Many2one(
        'field.pass.employee', string='Employee',
        ondelete='cascade', index=True, tracking=True,
    )
    vehicle_id = fields.Many2one(
        'field.pass.vehicle', string='Vehicle',
        ondelete='cascade', index=True, tracking=True,
    )
    entity_type = fields.Selection(
        [('employee', 'Employee'), ('vehicle', 'Vehicle')],
        compute='_compute_entity_type', store=True,
    )
    pass_type = fields.Selection(PASS_TYPES, string='Pass Type', required=True, tracking=True)
    pass_number = fields.Char(string='Pass Number', tracking=True)
    date_issued = fields.Date(string='Date Issued', tracking=True)
    date_expire = fields.Date(string='Expiry Date', tracking=True, index=True)
    application_status = fields.Selection(
        APP_STATUS, string='Application Status',
        default='no', required=True, tracking=True,
    )
    is_temp = fields.Boolean(
        string='Is Temp Pass', default=False,
        help='Check if this is a temporary pass covering an expired main pass.',
    )
    notes = fields.Text(string='Notes', tracking=True)
    attachment_pass = fields.Binary(string='Pass Document', attachment=True)
    attachment_pass_name = fields.Char(string='Pass Document Filename')
    company_id = fields.Many2one(
        'res.company', required=True,
        default=lambda self: self.env.company, tracking=True,
    )

    expiry_status = fields.Selection(
        EXPIRY_STATUS, compute='_compute_expiry', store=True,
    )
    days_to_expiry = fields.Integer(compute='_compute_expiry', store=True)
    display_name = fields.Char(compute='_compute_display', store=True)

    _sql_constraints = [
        ('unique_employee_pass', 'UNIQUE(employee_id, pass_type)',
         'Employee can only have one record per pass type.'),
        ('unique_vehicle_pass', 'UNIQUE(vehicle_id, pass_type)',
         'Vehicle can only have one record per pass type.'),
    ]

    # Import helper - link by Civil ID
    civil_id_number = fields.Char(string='Civil ID Number (for import)', store=False)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('civil_id_number') and not vals.get('employee_id'):
                emp = self.env['field.pass.employee'].search(
                    [('civil_id_number', '=', vals['civil_id_number'])], limit=1)
                if emp:
                    vals['employee_id'] = emp.id
            vals.pop('civil_id_number', None)
        return super().create(vals_list)

    @api.constrains('employee_id', 'vehicle_id')

    def _check_entity(self):
        for r in self:
            if r.employee_id and r.vehicle_id:
                raise ValidationError('A field pass cannot be linked to both an employee and a vehicle.')
            if not r.employee_id and not r.vehicle_id:
                raise ValidationError('A field pass must be linked to an employee or a vehicle.')

    @api.constrains('date_issued', 'date_expire')
    def _check_dates(self):
        for r in self:
            if r.date_issued and r.date_expire and r.date_expire < r.date_issued:
                raise ValidationError('Expiry date cannot be before issue date.')

    
    @api.constrains('pass_type', 'employee_id', 'vehicle_id')
    def _check_pass_type_allowed(self):
        for r in self:
            entity = r.employee_id or r.vehicle_id
            if not entity or not entity.department_id:
                continue
            dept = entity.department_id
            koc_types = ['KOC', 'RATQA_ABDALLY']
            wjo_types = ['WAFRA', 'FAWARES']
            if r.pass_type in koc_types and not dept.fp_client_koc:
                raise ValidationError(
                    f'Cannot add {dict(PASS_TYPES).get(r.pass_type)} - '
                    f'department "{dept.name}" is not a Kuwait Oil Company client.'
                )
            if r.pass_type in wjo_types and not dept.fp_client_wjo:
                raise ValidationError(
                    f'Cannot add {dict(PASS_TYPES).get(r.pass_type)} - '
                    f'department "{dept.name}" is not a Wafra Joint Operations client.'
                )
    
    @api.constrains('pass_type', 'employee_id')
    def _check_wafra_fawares(self):
        # FIX: this method previously had no @api.constrains decorator at
        # all, meaning it was defined but NEVER actually ran -- Odoo only
        # auto-invokes constraint methods that carry this decorator. WAFRA/
        # FAWARES passes could be created with zero WJO HSE Training on
        # record. This decorator is the entire fix.
        for r in self:
            if r.employee_id and r.pass_type in ('WAFRA', 'FAWARES'):
                if not r.employee_id.wjo_hse_training_attended:
                    raise ValidationError(
                        f'Cannot create {dict(PASS_TYPES).get(r.pass_type)} pass for '
                        f'{r.employee_id.name}: WJO HSE Training not attended.'
                    )

    @api.constrains('pass_type', 'employee_id', 'vehicle_id')
    def _check_documents_ready(self):
        # NEW -- field-pass gating, confirmed design, did not exist in this
        # module before:
        #   Employee KOC:            Civil ID must be valid
        #   Employee WAFRA/FAWARES:  Civil ID must be valid (WJO HSE checked separately above)
        #   Employee RATQA_ABDALLY:  a currently-valid KOC Field Pass must already exist
        #   Vehicle KOC:             Clearance + Registration + Inspection all valid
        #   Vehicle RATQA_ABDALLY:   a currently-valid KOC vehicle pass must already exist
        #   Vehicle WAFRA/FAWARES:   Registration valid (Inspection is optional)
        _OK = ('valid', 'warning')
        for r in self:
            if r.employee_id:
                emp = r.employee_id
                if r.pass_type in ('KOC', 'WAFRA', 'FAWARES'):
                    if emp.civil_id_status not in _OK:
                        raise ValidationError(
                            f'Cannot issue {dict(PASS_TYPES).get(r.pass_type)} for {emp.name}: '
                            f'Civil ID must be valid first.'
                        )
                if r.pass_type == 'RATQA_ABDALLY':
                    koc = emp.pass_ids.filtered(
                        lambda p: p.pass_type == 'KOC' and not p.is_temp and p.date_expire)
                    if not koc or not any(p.date_expire >= date.today() for p in koc):
                        raise ValidationError(
                            f'Cannot issue RATQA & Abdally GP for {emp.name}: '
                            f'a valid KOC Field Pass is required first.'
                        )

                if r.pass_type in ('PTW', 'KOC_LAPTOP'):
                    # MOVED from Employee-level constraint (Stage 2) — same
                    # rule, now applied here since these are real Pass
                    # records instead of Employee fields.
                    koc = emp.pass_ids.filtered(
                        lambda p: p.pass_type == 'KOC' and not p.is_temp and p.date_expire)
                    if not koc or not any(p.date_expire >= date.today() for p in koc):
                        raise ValidationError(
                            f'Cannot issue {dict(PASS_TYPES).get(r.pass_type)} for {emp.name}: '
                            f'a valid KOC Field Pass is required first.'
                        )

            if r.vehicle_id:
                veh = r.vehicle_id
                if r.pass_type == 'KOC':
                    missing = []
                    if veh.clearance_certificate_status not in _OK:
                        missing.append('Clearance Certificate')
                    if veh.registration_status not in _OK:
                        missing.append('Registration')
                    if veh.third_party_inspection_status not in _OK:
                        missing.append('3rd Party Inspection')
                    if missing:
                        raise ValidationError(
                            f'Cannot issue KOC Field Pass for {veh.plate_number}: '
                            f'the following must be valid first: {", ".join(missing)}.'
                        )
                if r.pass_type == 'RATQA_ABDALLY':
                    koc = veh.pass_ids.filtered(
                        lambda p: p.pass_type == 'KOC' and not p.is_temp and p.date_expire)
                    if not koc or not any(p.date_expire >= date.today() for p in koc):
                        raise ValidationError(
                            f'Cannot issue RATQA & Abdally GP for {veh.plate_number}: '
                            f'a valid KOC Field Pass is required first.'
                        )
                if r.pass_type in ('WAFRA', 'FAWARES'):
                    if veh.registration_status not in _OK:
                        raise ValidationError(
                            f'Cannot issue {dict(PASS_TYPES).get(r.pass_type)} for {veh.plate_number}: '
                            f'Registration must be valid first.'
                        )

    @api.depends('employee_id', 'vehicle_id')
    def _compute_entity_type(self):
        for r in self:
            r.entity_type = 'employee' if r.employee_id else ('vehicle' if r.vehicle_id else False)

    @api.depends('date_expire', 'pass_type', 'company_id')
    def _compute_expiry(self):
        for r in self:
            if not r.date_expire:
                r.expiry_status, r.days_to_expiry = 'na', 0
                continue
            delta = (r.date_expire - date.today()).days
            r.days_to_expiry = delta
            if delta < 0:
                r.expiry_status = 'expired'
            else:
                warn = self.env['field.pass.alert.config'].get_warn_days(
                    DOC_KEY_MAP.get(r.pass_type, 'fp_koc'),
                    r.company_id.id or self.env.company.id,
                )
                r.expiry_status = 'warning' if delta <= warn else 'valid'

    @api.depends('employee_id', 'vehicle_id', 'pass_type')
    def _compute_display(self):
        labels = dict(PASS_TYPES)
        for r in self:
            entity = (r.employee_id.name if r.employee_id
                      else r.vehicle_id.plate_number if r.vehicle_id else 'Unknown')
            r.display_name = f'{entity} - {labels.get(r.pass_type, r.pass_type or "")}'

    @api.model
    def cron_send_expiry_alerts(self):
        """
        Daily cron — scans every tracked document (Employee/Vehicle) and
        every Field Pass, and sends a one-time notification the first time
        each crosses into 'warning' or 'expired'.

        Design note: rather than trying to detect "today is exactly the
        crossing day" via date arithmetic, this checks CURRENT status
        (warning/expired) against the dedup log (already_sent(), scoped to
        the specific expiry date). This is more robust than exact-day
        matching — if the cron misses a day (server downtime, etc.), it
        naturally catches up on the next run instead of permanently
        missing that alert. The dedup log's expiry-date scoping is what
        makes this safe to re-check daily without ever double-sending: once
        logged for a given expiry date, it won't fire again until that
        expiry date changes (i.e. the document gets renewed).

        Confirmed scope: only 'warning'/'expired' fire alerts — the more
        nuanced temp-pass fallback states (temp_active/temp_warning/
        missing/not_required, used for Employee/Vehicle's rolled-up
        Summary-tab display) are intentionally NOT alerted on here; this
        cron only looks at each individual record's own straightforward
        valid/warning/expired/na status.
        """
        from .field_pass_notifications import send_fp_notification
        AlertLog = self.env['field.pass.alert.log']

        def _check_and_send(entity, doc_key, expiry_date, warn_days, label, res_model):
            if not expiry_date:
                return
            status, _days = entity._calc(expiry_date, warn_days)
            if status not in ('warning', 'expired'):
                return
            if AlertLog.already_sent(res_model, entity.id, doc_key, status, expiry_date):
                return
            send_fp_notification(
                self.env, entity, label, status,
                document_type_key=doc_key, expiry_date=expiry_date,
            )

        # ── Employee documents ──────────────────────────────────────────
        EMPLOYEE_DOC_FIELDS = [
            ('passport', 'passport_validity', 'Passport'),
            ('residency', 'residency_validity', 'Residency'),
            ('civil_id', 'civil_id_validity', 'Civil ID'),
            ('driving_license', 'driving_license_validity', 'Driving License'),
            ('driving_authority', 'driving_authority_validity', 'Driving Authority'),
            # driving_hse_expiry_date is OPTIONAL (see field_pass_employee.py)
            # — "valid once obtained" with no expiry set should never alert,
            # which _check_and_send already handles via the `if not expiry_date`
            # guard above.
            ('driving_hse', 'driving_hse_expiry_date', 'Driving HSE Training'),
        ]
        employees = self.env['field.pass.employee'].search([('active', '=', True)])
        for emp in employees:
            for doc_key, field_name, label in EMPLOYEE_DOC_FIELDS:
                if doc_key == 'residency' and emp.gcc_national:
                    continue  # matches _compute_statuses: always 'na' for GCC nationals
                _check_and_send(
                    emp, doc_key, getattr(emp, field_name),
                    emp._warn(doc_key), label, 'field.pass.employee',
                )

        # ── Vehicle documents ───────────────────────────────────────────
        VEHICLE_DOC_FIELDS = [
            ('registration', 'registration_expiry_date', 'Registration'),
            ('clearance', 'clearance_certificate_expiry', 'Clearance Certificate'),
            ('third_party', 'third_party_inspection_expiry', '3rd Party Inspection'),
        ]
        vehicles = self.env['field.pass.vehicle'].search([('active', '=', True)])
        for veh in vehicles:
            for doc_key, field_name, label in VEHICLE_DOC_FIELDS:
                _check_and_send(
                    veh, doc_key, getattr(veh, field_name),
                    veh._warn(doc_key), label, 'field.pass.vehicle',
                )

        # ── Field Passes (KOC/RATQA/WAFRA/FAWARES/PTW/KOC Laptop/TEMP) ──
        passes = self.search([('date_expire', '!=', False)])
        for p in passes:
            entity = p.employee_id or p.vehicle_id
            if not entity:
                continue
            warn_days = self.env['field.pass.alert.config'].get_warn_days(
                DOC_KEY_MAP.get(p.pass_type, 'fp_koc'),
                entity.company_id.id or self.env.company.id,
            )
            label = dict(PASS_TYPES).get(p.pass_type, p.pass_type)
            label = label.split(' - ')[0] if ' - ' in label else label
            # NOTE: logged against the Pass record's own id (res_model=
            # 'field.pass'), not the parent entity's id — keeps the dedup
            # key unique per Pass record even if an entity has multiple
            # passes of the same type (e.g. TEMP + main) with different
            # expiry dates.
            status, _days = entity._calc(p.date_expire, warn_days)
            if status not in ('warning', 'expired'):
                continue
            if AlertLog.already_sent('field.pass', p.id, p.pass_type, status, p.date_expire):
                continue
            send_fp_notification(
                self.env, entity, label, status,
                document_type_key=p.pass_type, expiry_date=p.date_expire,
            )

        # ── Company Documents — confirmed design: this never had a working
        # notification mechanism before (Focal Point fields existed but
        # were never wired to actually send anything). Not department-
        # scoped like Employee/Vehicle — goes to every GRO-tier user
        # instead, via notify_track rather than send_fp_notification (which
        # assumes an entity.department_id that Company Documents don't
        # have). ──────────────────────────────────────────────────────────
        from .field_pass_notifications import notify_track, STATUS_WORDS
        company_docs = self.env['field.pass.company.document'].search([
            ('status', 'in', ('warning', 'expired')),
            ('active', '=', True),
        ])
        for doc in company_docs:
            if AlertLog.already_sent(
                'field.pass.company.document', doc.id, doc.name, doc.status, doc.validity_date):
                continue
            status_word = STATUS_WORDS.get(doc.status, doc.status)
            subject = f'Field Pass Update — {doc.name} {status_word}'
            body_html = (
                f'<p><b>{doc.name}</b> for <b>{doc.company_id.name}</b></p>'
                f'<p>Status: <b>{status_word}</b></p>'
                f'<p>Related Authority: {doc.related_authority or "—"}</p>'
            )
            notify_track(self.env, 'field_pass_tracker.group_fp_viewer', subject, body_html)
            AlertLog.create({
                'res_model': 'field.pass.company.document',
                'res_id': doc.id,
                'entity_name': doc.company_id.name,
                'document_type': doc.name,
                'document_expiry_date': doc.validity_date,
                'alert_type': doc.status,
                'recipient_emails': 'GRO (all)',
            })
