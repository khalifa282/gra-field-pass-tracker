# -*- coding: utf-8 -*-
from odoo import models, fields, api
from datetime import date, timedelta


class FieldPassVehicle(models.Model):
    _name = 'field.pass.vehicle'
    _description = 'Field Pass Vehicle'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'department_id, plate_number'
    _rec_name = 'plate_number'

    plate_number = fields.Char(string='Plate Number', required=True, tracking=True)
    vehicle_type = fields.Selection(
        [('Pickup', 'Pickup'), ('SUV', 'SUV'), ('Sedan', 'Sedan'),
         ('Van', 'Van'), ('Truck', 'Truck'), ('Heavy', 'Heavy Equipment'),
         ('Other', 'Other')],
        string='Vehicle Type', required=True, tracking=True,
    )
    vehicle_description = fields.Char(string='Description', tracking=True)
    model_year = fields.Char(string='Model Year', tracking=True)
    unit_serial_number = fields.Char(string='Unit / Serial Number', tracking=True)
    active = fields.Boolean(default=True, tracking=True)
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
    department_id = fields.Many2one('hr.department', string='Department', required=True,
                                    tracking=True, ondelete='restrict')
    contract_id = fields.Many2one('field.pass.contract', string='Contract', tracking=True,
                                   domain="[('department_id','=',department_id),('active','=',True)]")
    remarks = fields.Text(string='Remarks', tracking=True)

    dept_has_koc = fields.Boolean(compute='_compute_dept_clients', store=False)
    dept_has_wjo = fields.Boolean(compute='_compute_dept_clients', store=False)

    allowed_pass_types = fields.Char(compute='_compute_allowed_pass_types', store=False)

    @api.depends('department_id.fp_client_koc', 'department_id.fp_client_wjo')
    def _compute_allowed_pass_types(self):
        for v in self:
            types = ['TEMP']
            if v.department_id and v.department_id.fp_client_koc:
                types += ['KOC', 'RATQA_ABDALLY']
            if v.department_id and v.department_id.fp_client_wjo:
                types += ['WAFRA', 'FAWARES']
            v.allowed_pass_types = ','.join(types)

    @api.depends('department_id', 'department_id.fp_client_koc', 'department_id.fp_client_wjo')
    def _compute_dept_clients(self):
        for v in self:
            v.dept_has_koc = v.department_id.fp_client_koc if v.department_id else False
            v.dept_has_wjo = v.department_id.fp_client_wjo if v.department_id else False

    # ── Registration ──────────────────────────────────────────────────────────
    registration_expiry_date = fields.Date(string='Registration Expiry', tracking=True)
    registration_status = fields.Selection(
        [('valid','Valid'),('warning','Warning'),('expired','Expired'),('na','Not Required')],
        compute='_compute_statuses', store=True)
    registration_days = fields.Integer(compute='_compute_statuses', store=True)
    attachment_registration = fields.Binary(string='Registration Document', attachment=True)
    attachment_registration_name = fields.Char()

    # ── 3rd Party Inspection ──────────────────────────────────────────────────
    third_party_inspection_date = fields.Date(string='3rd Party Inspection Date', tracking=True)
    third_party_inspection_expiry = fields.Date(
        string='3rd Party Inspection Expiry', compute='_compute_inspection_expiry', store=True)
    third_party_inspection_status = fields.Selection(
        [('valid','Valid'),('warning','Warning'),('expired','Expired'),('na','Not Required')],
        compute='_compute_statuses', store=True)
    third_party_inspection_days = fields.Integer(compute='_compute_statuses', store=True)
    attachment_third_party = fields.Binary(string='3rd Party Document', attachment=True)
    attachment_third_party_name = fields.Char()

    # ── Clearance Certificate ─────────────────────────────────────────────────
    clearance_certificate_expiry = fields.Date(string='Clearance Certificate Expiry', tracking=True)
    clearance_certificate_status = fields.Selection(
        [('valid','Valid'),('warning','Warning'),('expired','Expired'),('na','Not Required')],
        compute='_compute_statuses', store=True)
    clearance_certificate_days = fields.Integer(compute='_compute_statuses', store=True)
    attachment_clearance = fields.Binary(string='Clearance Document', attachment=True)
    attachment_clearance_name = fields.Char()

    overall_doc_status = fields.Selection(
        [('valid','Valid'),('warning','Warning'),('expired','Expired')],
        compute='_compute_overall_doc', store=True)

    # ── Field Passes ──────────────────────────────────────────────────────────
    pass_ids = fields.One2many('field.pass', 'vehicle_id', string='Field Passes')
    pass_count = fields.Integer(compute='_compute_pass_count')

    pass_koc_status = fields.Selection(
        [('valid','Valid'),('warning','Expiring Soon'),('expired','Expired'),
         ('temp_active','Temp Active'),('temp_warning','Temp Expiring'),
         ('missing','No Expiry Date - لا يوجد تاريخ'),('not_required','Not Required')],
        compute='_compute_pass_statuses', store=True)
    pass_ratqa_status = fields.Selection(
        [('valid','Valid'),('warning','Expiring Soon'),('expired','Expired'),
         ('temp_active','Temp Active'),('temp_warning','Temp Expiring'),
         ('missing','No Expiry Date - لا يوجد تاريخ'),('not_required','Not Required')],
        compute='_compute_pass_statuses', store=True)
    pass_wafra_status = fields.Selection(
        [('valid','Valid'),('warning','Expiring Soon'),('expired','Expired'),
         ('temp_active','Temp Active'),('temp_warning','Temp Expiring'),
         ('missing','No Expiry Date - لا يوجد تاريخ'),('not_required','Not Required')],
        compute='_compute_pass_statuses', store=True)
    pass_fawares_status = fields.Selection(
        [('valid','Valid'),('warning','Expiring Soon'),('expired','Expired'),
         ('temp_active','Temp Active'),('temp_warning','Temp Expiring'),
         ('missing','No Expiry Date - لا يوجد تاريخ'),('not_required','Not Required')],
        compute='_compute_pass_statuses', store=True)

    overall_status = fields.Selection(
        [('valid','Valid'),('warning','Warning'),('expired','Expired'),('missing','Missing Pass')],
        compute='_compute_overall', store=True)

    # ── History tabs ──────────────────────────────────────────────────────────
    renewal_history_ids = fields.One2many(
        'field.pass.renewal', 'vehicle_id',
        string='Document Renewal History', readonly=True)
    pass_app_history_ids = fields.One2many(
        'field.pass.application', 'vehicle_id',
        string='Field Pass History', readonly=True)

    # ── Summary Tab ───────────────────────────────────────────────────────────
    def _get_doc_validity(self, expiry_field, warn_days=30):
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

    def _get_renewal_status_v(self, doc_type):
        latest = self.env['field.pass.renewal'].search([
            ('vehicle_id', '=', self.id),
            ('document_type', '=', doc_type),
        ], order='event_date desc', limit=1)
        if not latest:
            return 'none'
        return latest.event_type

    def _get_pass_validity_v(self, pass_type):
        from datetime import date as dt
        rec = self.env['field.pass'].search([
            ('vehicle_id', '=', self.id),
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

    def _get_app_status_v(self, pass_type):
        latest = self.env['field.pass.application'].search([
            ('vehicle_id', '=', self.id),
            ('pass_type', '=', pass_type),
        ], order='event_date desc', limit=1)
        if not latest:
            return 'none'
        return latest.state

    @api.depends('registration_expiry_date', 'third_party_inspection_expiry',
                 'clearance_certificate_expiry', 'renewal_history_ids', 'pass_app_history_ids')
    def _compute_summary_v(self):
        for r in self:
            r.sv_registration = r._get_doc_validity('registration_expiry_date')
            r.sv_third_party = r._get_doc_validity('third_party_inspection_expiry')
            r.sv_clearance = r._get_doc_validity('clearance_certificate_expiry')
            r.sa_registration = r._get_renewal_status_v('registration')
            r.sa_third_party = r._get_renewal_status_v('third_party')
            r.sa_clearance = r._get_renewal_status_v('clearance')
            r.sv_koc_pass = r._get_pass_validity_v('KOC')
            r.sv_ratqa_pass = r._get_pass_validity_v('RATQA_ABDALLY')
            r.sv_wafra_pass = r._get_pass_validity_v('WAFRA')
            r.sv_fawares_pass = r._get_pass_validity_v('FAWARES')
            r.sv_temp_pass = r._get_pass_validity_v('TEMP')
            r.sa_koc_pass = r._get_app_status_v('KOC')
            r.sa_ratqa_pass = r._get_app_status_v('RATQA_ABDALLY')
            r.sa_wafra_pass = r._get_app_status_v('WAFRA')
            r.sa_fawares_pass = r._get_app_status_v('FAWARES')
            r.sa_temp_pass = r._get_app_status_v('TEMP')

    _VALIDITY = [('valid','Valid'),('warning','Expiring Soon'),('expired','Expired'),('missing','No Expiry Date - لا يوجد تاريخ')]
    _APP_ST = [('none','-'),('submitted','Submitted'),('rejected','Rejected'),('issued','Issued')]

    sv_registration = fields.Selection(_VALIDITY, compute='_compute_summary_v', string='Validity')
    sv_third_party = fields.Selection(_VALIDITY, compute='_compute_summary_v', string='Validity')
    sv_clearance = fields.Selection(_VALIDITY, compute='_compute_summary_v', string='Validity')
    sv_koc_pass = fields.Selection(_VALIDITY, compute='_compute_summary_v', string='Validity')
    sv_ratqa_pass = fields.Selection(_VALIDITY, compute='_compute_summary_v', string='Validity')
    sv_wafra_pass = fields.Selection(_VALIDITY, compute='_compute_summary_v', string='Validity')
    sv_fawares_pass = fields.Selection(_VALIDITY, compute='_compute_summary_v', string='Validity')
    sv_temp_pass = fields.Selection(_VALIDITY, compute='_compute_summary_v', string='Validity')
    sa_registration = fields.Selection(_APP_ST, compute='_compute_summary_v', string='Application Status')
    sa_third_party = fields.Selection(_APP_ST, compute='_compute_summary_v', string='Application Status')
    sa_clearance = fields.Selection(_APP_ST, compute='_compute_summary_v', string='Application Status')
    sa_koc_pass = fields.Selection(_APP_ST, compute='_compute_summary_v', string='Application Status')
    sa_ratqa_pass = fields.Selection(_APP_ST, compute='_compute_summary_v', string='Application Status')
    sa_wafra_pass = fields.Selection(_APP_ST, compute='_compute_summary_v', string='Application Status')
    sa_fawares_pass = fields.Selection(_APP_ST, compute='_compute_summary_v', string='Application Status')
    sa_temp_pass = fields.Selection(_APP_ST, compute='_compute_summary_v', string='Application Status')

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
        main = self.pass_ids.filtered(lambda p: p.pass_type == pass_type and not p.is_temp)
        temp = self.pass_ids.filtered(lambda p: p.pass_type == 'TEMP' and p.is_temp)
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

    @api.depends('third_party_inspection_date', 'company_id')
    def _compute_inspection_expiry(self):
        for v in self:
            if v.third_party_inspection_date:
                dur = self.env['field.pass.alert.config'].get_inspection_duration(
                    v.company_id.id or self.env.company.id)
                v.third_party_inspection_expiry = v.third_party_inspection_date + timedelta(days=dur)
            else:
                v.third_party_inspection_expiry = False

    @api.depends('registration_expiry_date', 'third_party_inspection_expiry',
                 'clearance_certificate_expiry', 'company_id')
    def _compute_statuses(self):
        for v in self:
            v.registration_status, v.registration_days = v._calc(
                v.registration_expiry_date, v._warn('registration'))
            v.third_party_inspection_status, v.third_party_inspection_days = v._calc(
                v.third_party_inspection_expiry, v._warn('third_party_inspection'))
            v.clearance_certificate_status, v.clearance_certificate_days = v._calc(
                v.clearance_certificate_expiry, v._warn('clearance_certificate'))

    @api.depends('registration_status', 'third_party_inspection_status', 'clearance_certificate_status')
    def _compute_overall_doc(self):
        RANK = {'expired': 2, 'warning': 1, 'valid': 0, 'na': -1}
        for v in self:
            worst = max(RANK.get(v.registration_status, -1),
                        RANK.get(v.third_party_inspection_status, -1),
                        RANK.get(v.clearance_certificate_status, -1))
            v.overall_doc_status = ('expired' if worst == 2 else 'warning' if worst == 1 else 'valid')

    @api.depends('pass_ids', 'pass_ids.pass_type', 'pass_ids.date_expire', 'pass_ids.is_temp',
                 'department_id', 'department_id.fp_client_koc', 'department_id.fp_client_wjo')
    def _compute_pass_statuses(self):
        for v in self:
            dept = v.department_id
            koc = dept.fp_client_koc if dept else False
            wjo = dept.fp_client_wjo if dept else False
            warn = v._warn('fp_koc')
            v.pass_koc_status     = v._calc_pass_status('KOC', koc, warn)
            v.pass_ratqa_status   = v._calc_pass_status('RATQA_ABDALLY', koc, warn)
            v.pass_wafra_status   = v._calc_pass_status('WAFRA', wjo, warn)
            v.pass_fawares_status = v._calc_pass_status('FAWARES', wjo, warn)

    @api.depends('overall_doc_status', 'pass_koc_status', 'pass_ratqa_status',
                 'pass_wafra_status', 'pass_fawares_status')
    def _compute_overall(self):
        RANK = {'expired': 3, 'missing': 3, 'temp_warning': 2, 'warning': 2,
                'temp_active': 1, 'valid': 0, 'not_required': -1, 'na': -1}
        PASS_FIELDS = ['pass_koc_status', 'pass_ratqa_status',
                       'pass_wafra_status', 'pass_fawares_status']
        for v in self:
            doc_rank = RANK.get(v.overall_doc_status, 0)
            pass_rank = max(RANK.get(getattr(v, f, 'not_required'), -1) for f in PASS_FIELDS)
            worst = max(doc_rank, pass_rank)
            if worst >= 3:
                v.overall_status = 'expired' if doc_rank >= 3 else 'missing'
            elif worst == 2:
                v.overall_status = 'warning'
            else:
                v.overall_status = 'valid'

    def _compute_pass_count(self):
        for v in self:
            v.pass_count = len(v.pass_ids)

    def action_view_passes(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Field Passes — {self.plate_number}',
            'res_model': 'field.pass',
            'view_mode': 'tree,form',
            'domain': [('vehicle_id', '=', self.id)],
            'context': {'default_vehicle_id': self.id},
        }
