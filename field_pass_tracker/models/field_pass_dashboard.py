# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError


class FieldPassDashboard(models.Model):
    # Use regular Model instead of TransientModel
    # This prevents Odoo garbage collector from deleting records
    _name = 'field.pass.dashboard'
    _description = 'Field Pass Dashboard'

    name = fields.Char(default='Dashboard', readonly=True)
    department_id = fields.Many2one('hr.department', string='Filter by Department')
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    def _search_scoped(self, model_name, domain):
        """
        Confirmed design: search a model, respecting the calling user's OWN
        record rules (so OPS's department-scoping wall applies naturally
        here too, not just on the Employee/Vehicle list screens) — but
        falling back to sudo() ONLY if the user has no model-level access
        at all (e.g. HR on Vehicle), so the Dashboard doesn't crash for
        them. Blanket sudo() everywhere was the earlier, wrong fix — it
        accidentally bypassed the department rule for OPS too, not just
        the intended HR model-access gap.
        """
        Model = self.env[model_name]
        if Model.check_access_rights('read', raise_exception=False):
            return Model.search(domain)
        return Model.sudo().search(domain)

    def _search_count_scoped(self, model_name, domain):
        """Same principle as _search_scoped, for search_count specifically."""
        Model = self.env[model_name]
        if Model.check_access_rights('read', raise_exception=False):
            return Model.search_count(domain)
        return Model.sudo().search_count(domain)

    # ── SUMMARY TOTALS ────────────────────────────────────────────────────────
    emp_doc_expired  = fields.Integer(compute='_compute_stats', store=False)
    emp_doc_warning  = fields.Integer(compute='_compute_stats', store=False)
    emp_doc_valid    = fields.Integer(compute='_compute_stats', store=False)
    emp_total        = fields.Integer(compute='_compute_stats', store=False)
    emp_pass_expired = fields.Integer(compute='_compute_stats', store=False)
    emp_pass_warning = fields.Integer(compute='_compute_stats', store=False)
    emp_pass_missing = fields.Integer(compute='_compute_stats', store=False)
    emp_pass_temp    = fields.Integer(compute='_compute_stats', store=False)
    emp_pass_valid   = fields.Integer(compute='_compute_stats', store=False)
    veh_doc_expired  = fields.Integer(compute='_compute_stats', store=False)
    veh_doc_warning  = fields.Integer(compute='_compute_stats', store=False)
    veh_doc_valid    = fields.Integer(compute='_compute_stats', store=False)
    veh_total        = fields.Integer(compute='_compute_stats', store=False)
    veh_pass_expired = fields.Integer(compute='_compute_stats', store=False)
    veh_pass_warning = fields.Integer(compute='_compute_stats', store=False)
    veh_pass_missing = fields.Integer(compute='_compute_stats', store=False)
    veh_pass_temp    = fields.Integer(compute='_compute_stats', store=False)
    veh_pass_valid   = fields.Integer(compute='_compute_stats', store=False)


    # ── Progress Tab Fields ───────────────────────────────────────────────────

    # ── Employees Tab Fields ──────────────────────────────────────────────────

    # ── Missing fields ────────────────────────────────────────────────────────


    # ── Progress Tab ──────────────────────────────────────────────────────────
    renewal_submitted  = fields.Integer(compute='_compute_stats', store=False)
    renewal_rejected   = fields.Integer(compute='_compute_stats', store=False)
    pass_app_submitted = fields.Integer(compute='_compute_stats', store=False)
    pass_app_rejected  = fields.Integer(compute='_compute_stats', store=False)
    recent_renewal_ids = fields.Many2many(
        'field.pass.renewal', 'fp_dash_renewal_rel', 'dash_id', 'renewal_id',
        compute='_compute_stats', store=False, string='Recent Renewals')
    recent_app_ids = fields.Many2many(
        'field.pass.application', 'fp_dash_app_rel', 'dash_id', 'app_id',
        compute='_compute_stats', store=False, string='Recent Applications')

    # ── Employees Tab ─────────────────────────────────────────────────────────
    emp_field_count  = fields.Integer(compute='_compute_stats', store=False)
    emp_driver_count = fields.Integer(compute='_compute_stats', store=False)
    emp_office_count = fields.Integer(compute='_compute_stats', store=False)

    # ── Status labels ─────────────────────────────────────────────────────────
    emp_doc_status  = fields.Char(compute='_compute_stats', store=False)
    veh_doc_status  = fields.Char(compute='_compute_stats', store=False)

    department_line_ids = fields.One2many(
        'field.pass.dashboard.dept', 'dashboard_id', string='Department Breakdown',
    )
    company_line_ids = fields.One2many(
        'field.pass.dashboard.company', 'dashboard_id', string='Company Documents Breakdown',
    )
    company_docs_html = fields.Html(
        compute='_compute_company_docs_html', sanitize=False,
        help='Built as raw HTML (not an embedded kanban view) — after two attempts at '
             'overriding the kanban CSS to force full-width stacking per company '
             'without success, this sidesteps the problem entirely by generating exact, '
             'guaranteed markup directly, matching the existing static card style '
             'used for Employee/Vehicle Documents above.',
    )
    company_doc_alert_ids = fields.Many2many(
        'field.pass.company.document', 'fp_dash_company_doc_alert_rel', 'dash_id', 'doc_id',
        compute='_compute_company_doc_alerts', store=False,
        string='Company Documents Needing Attention',
        help='Overview list, confirmed design — not an event log (Company Documents have no '
             'submit/reject/issue workflow, unlike Employee/Vehicle documents). Just every '
             'document currently in warning or expired status, most urgent first.',
    )

    @api.depends('company_line_ids.doc_warning', 'company_line_ids.doc_expired')
    def _compute_company_doc_alerts(self):
        for rec in self:
            docs = self.env['field.pass.company.document'].sudo().search([
                ('status', 'in', ('warning', 'expired')),
                ('active', '=', True),
            ], order='status asc, validity_date asc')
            rec.company_doc_alert_ids = [(6, 0, docs.ids)]

    # ── HR tab — confirmed design: "in-flight" means not yet Draft (not
    # submitted, nothing to track yet) and not in the final SUCCESS state
    # (Completed/Closed, already done). Rejected requests ARE included —
    # they're not "closed" in the Work Visa model's own terminology, and
    # showing them here surfaces things that need a Reopen decision rather
    # than silently disappearing from view. ─────────────────────────────────
    hr_residency_draft = fields.Integer(compute='_compute_hr_stats', store=False)
    hr_residency_active = fields.Integer(compute='_compute_hr_stats', store=False)
    hr_residency_rejected = fields.Integer(compute='_compute_hr_stats', store=False)
    hr_residency_completed = fields.Integer(compute='_compute_hr_stats', store=False)
    hr_visa_draft = fields.Integer(compute='_compute_hr_stats', store=False)
    hr_visa_active = fields.Integer(compute='_compute_hr_stats', store=False)
    hr_visa_rejected = fields.Integer(compute='_compute_hr_stats', store=False)
    hr_visa_closed = fields.Integer(compute='_compute_hr_stats', store=False)

    hr_residency_alert_ids = fields.Many2many(
        'field.pass.hr.residency.request', 'fp_dash_hr_residency_rel', 'dash_id', 'req_id',
        compute='_compute_hr_stats', store=False, string='Residency Requests In Progress',
    )
    hr_visa_alert_ids = fields.Many2many(
        'field.pass.hr.visa.request', 'fp_dash_hr_visa_rel', 'dash_id', 'req_id',
        compute='_compute_hr_stats', store=False, string='Work Visa Requests In Progress',
    )

    @api.depends('company_line_ids')  # cheap, unrelated trigger — see note on similar fields above
    def _compute_hr_stats(self):
        Residency = self.env['field.pass.hr.residency.request'].sudo()
        Visa = self.env['field.pass.hr.visa.request'].sudo()
        for rec in self:
            rec.hr_residency_draft = Residency.search_count([('state', '=', 'draft')])
            rec.hr_residency_rejected = Residency.search_count([('state', '=', 'rejected')])
            rec.hr_residency_completed = Residency.search_count([('state', '=', 'completed')])
            residency_active = Residency.search(
                [('state', 'not in', ('draft', 'completed', 'closed'))], order='create_date desc')
            rec.hr_residency_active = len(residency_active)
            rec.hr_residency_alert_ids = [(6, 0, residency_active.ids)]

            rec.hr_visa_draft = Visa.search_count([('state', '=', 'draft')])
            rec.hr_visa_rejected = Visa.search_count([('state', '=', 'rejected')])
            rec.hr_visa_closed = Visa.search_count([('state', '=', 'closed')])
            visa_active = Visa.search(
                [('state', 'not in', ('draft', 'closed', 'rejected_closed'))], order='create_date desc')
            rec.hr_visa_active = len(visa_active)
            rec.hr_visa_alert_ids = [(6, 0, visa_active.ids)]

    @api.depends('company_line_ids.doc_valid', 'company_line_ids.doc_warning',
                 'company_line_ids.doc_expired', 'company_line_ids.doc_total')
    def _compute_company_docs_html(self):
        card = '''
            <div style="background:{bg};border:1px solid {border};border-left:4px solid {accent};
                        border-radius:10px;padding:16px 14px;text-align:center;height:90px;
                        display:flex;flex-direction:column;justify-content:center;">
                <div style="font-size:28px;font-weight:700;color:{accent};line-height:1;">{value}</div>
                <div style="font-size:11px;font-weight:600;color:{accent};margin-top:6px;">{label}</div>
            </div>
        '''
        for rec in self:
            blocks = []
            for line in rec.sudo().company_line_ids:
                blocks.append(f'''
                    <div style="width:100%;display:block;margin-bottom:22px;">
                        <div style="font-size:15px;font-weight:700;color:#1e293b;margin-bottom:10px;">
                            {line.company_name}
                        </div>
                        <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:10px;">
                            {card.format(bg='#fee2e2', border='#fca5a5', accent='#dc2626', value=line.doc_expired, label='Expired - منتهي')}
                            {card.format(bg='#fef3c7', border='#fcd34d', accent='#d97706', value=line.doc_warning, label='Expiring Soon - ينتهي قريباً')}
                            {card.format(bg='#dcfce7', border='#86efac', accent='#16a34a', value=line.doc_valid, label='Valid - ساري')}
                            {card.format(bg='#f8fafc', border='#e2e8f0', accent='#334155', value=line.doc_total, label='Total - الإجمالي')}
                        </div>
                    </div>
                ''')
            rec.company_docs_html = ''.join(blocks) if blocks else '<p style="color:#94a3b8;">No companies yet.</p>'

    @api.depends('department_id', 'company_id')
    def _compute_stats(self):
        for rec in self:
            cid = rec.company_id.id or self.env.company.id
            PASS_FIELDS = ['pass_koc_status', 'pass_ratqa_status',
                           'pass_wafra_status', 'pass_fawares_status']

            emp_domain = [('company_id', '=', cid), ('active', '=', True)]
            veh_domain = [('company_id', '=', cid), ('active', '=', True)]
            if rec.department_id:
                emp_domain.append(('department_id', '=', rec.department_id.id))
                veh_domain.append(('department_id', '=', rec.department_id.id))

            emps = self._search_scoped('field.pass.employee', emp_domain)
            vehs = self._search_scoped('field.pass.vehicle', veh_domain)
            rec.emp_total        = len(emps)
            rec.emp_doc_expired  = len(emps.filtered(lambda e: e.overall_doc_status == 'expired'))
            rec.emp_doc_warning  = len(emps.filtered(lambda e: e.overall_doc_status == 'warning'))
            rec.emp_doc_valid    = len(emps.filtered(lambda e: e.overall_doc_status == 'valid'))

            def emp_pass_has(e, statuses):
                return any(getattr(e, f) in statuses for f in PASS_FIELDS)

            rec.emp_pass_expired = len(emps.filtered(lambda e: emp_pass_has(e, ['expired'])))
            rec.emp_pass_warning = len(emps.filtered(lambda e: emp_pass_has(e, ['warning'])))
            rec.emp_pass_missing = len(emps.filtered(lambda e: emp_pass_has(e, ['missing'])))
            rec.emp_pass_temp    = len(emps.filtered(lambda e: emp_pass_has(e, ['temp_active', 'temp_warning'])))
            rec.emp_pass_valid   = len(emps.filtered(
                lambda e: all(getattr(e, f) in ['valid', 'not_required'] for f in PASS_FIELDS)))

            rec.veh_total        = len(vehs)
            rec.veh_doc_expired  = len(vehs.filtered(lambda v: v.overall_doc_status == 'expired'))
            rec.veh_doc_warning  = len(vehs.filtered(lambda v: v.overall_doc_status == 'warning'))
            rec.veh_doc_valid    = len(vehs.filtered(lambda v: v.overall_doc_status == 'valid'))

            def veh_pass_has(v, statuses):
                return any(getattr(v, f) in statuses for f in PASS_FIELDS)

            rec.veh_pass_expired = len(vehs.filtered(lambda v: veh_pass_has(v, ['expired'])))
            rec.veh_pass_warning = len(vehs.filtered(lambda v: veh_pass_has(v, ['warning'])))
            rec.veh_pass_missing = len(vehs.filtered(lambda v: veh_pass_has(v, ['missing'])))
            rec.veh_pass_temp    = len(vehs.filtered(lambda v: veh_pass_has(v, ['temp_active', 'temp_warning'])))
            rec.veh_pass_valid   = len(vehs.filtered(
                lambda v: all(getattr(v, f) in ['valid', 'not_required'] for f in PASS_FIELDS)))

            # Employee job type counts
            rec.emp_field_count  = len(emps.filtered(lambda e: e.job_type == 'Field'))
            rec.emp_driver_count = len(emps.filtered(lambda e: e.job_type == 'Driver'))
            rec.emp_office_count = len(emps.filtered(lambda e: e.job_type == 'Office'))

            # Overall status labels - compute from local vars to avoid cache miss
            _emp_doc_exp = len(emps.filtered(lambda e: e.overall_doc_status == 'expired'))
            _emp_doc_warn = len(emps.filtered(lambda e: e.overall_doc_status == 'warning'))
            _emp_p_exp = len(emps.filtered(lambda e: emp_pass_has(e, ['expired'])))
            _emp_p_miss = len(emps.filtered(lambda e: emp_pass_has(e, ['missing'])))
            _emp_p_warn = len(emps.filtered(lambda e: emp_pass_has(e, ['warning'])))
            _veh_doc_exp = len(vehs.filtered(lambda v: v.overall_doc_status == 'expired'))
            _veh_doc_warn = len(vehs.filtered(lambda v: v.overall_doc_status == 'warning'))
            _veh_p_exp = len(vehs.filtered(lambda v: veh_pass_has(v, ['expired'])))
            _veh_p_miss = len(vehs.filtered(lambda v: veh_pass_has(v, ['missing'])))
            _veh_p_warn = len(vehs.filtered(lambda v: veh_pass_has(v, ['warning'])))
            rec.emp_doc_status  = 'danger' if _emp_doc_exp else 'warning' if _emp_doc_warn else 'ok'
            rec.veh_doc_status  = 'danger' if _veh_doc_exp else 'warning' if _veh_doc_warn else 'ok'
            rec.emp_pass_status = 'danger' if _emp_p_exp or _emp_p_miss else 'warning' if _emp_p_warn else 'ok'
            rec.veh_pass_status = 'danger' if _veh_p_exp or _veh_p_miss else 'warning' if _veh_p_warn else 'ok'

            # Progress tab - active submissions
            rec.renewal_submitted  = self._search_count_scoped('field.pass.renewal', [('event_type', '=', 'submitted')])
            rec.renewal_rejected   = self._search_count_scoped('field.pass.renewal', [('event_type', '=', 'rejected')])
            rec.pass_app_submitted = self._search_count_scoped('field.pass.application', [('state', '=', 'submitted')])
            rec.pass_app_rejected  = self._search_count_scoped('field.pass.application', [('state', '=', 'rejected')])

            # Recent activity (last 20)
            recent_renewals = self._search_scoped('field.pass.renewal', []).sorted('event_date', reverse=True)[:20]
            rec.recent_renewal_ids = [(6, 0, recent_renewals.ids)]
            recent_apps = self._search_scoped('field.pass.application', []).sorted('event_date', reverse=True)[:20]
            rec.recent_app_ids = [(6, 0, recent_apps.ids)]

            # ── Statistics ────────────────────────────────────────────────────
            def calc_days(submitted_events, issued_events):
                """Match submitted->issued pairs and return list of days."""
                days_list = []
                for issued in issued_events:
                    entity_key = (issued.employee_id.id, issued.vehicle_id.id,
                                  getattr(issued, 'document_type', None) or getattr(issued, 'pass_type', None))
                    # Find latest submitted before this issued
                    matching = [s for s in submitted_events
                                if (s.employee_id.id, s.vehicle_id.id,
                                    getattr(s, 'document_type', None) or getattr(s, 'pass_type', None)) == entity_key
                                and s.event_date <= issued.event_date]
                    if matching:
                        latest_sub = max(matching, key=lambda x: x.event_date)
                        delta = (issued.event_date - latest_sub.event_date).days
                        if delta >= 0:
                            days_list.append((delta, issued))
                return days_list

            # Document renewal stats
            all_renewals = self._search_scoped('field.pass.renewal', [])
            submitted_r = all_renewals.filtered(lambda r: r.event_type == 'submitted')
            issued_r = all_renewals.filtered(lambda r: r.event_type == 'issued')
            doc_pairs = calc_days(submitted_r, issued_r)

            # Pass application stats
            all_apps = self._search_scoped('field.pass.application', [])
            submitted_a = all_apps.filtered(lambda a: a.state == 'submitted')
            issued_a = all_apps.filtered(lambda a: a.state == 'issued')
            pass_pairs = calc_days(submitted_a, issued_a)

            # ── HR Request stats — confirmed design: folded into the overall
            # Fastest/Slowest/Total Completed numbers alongside documents and
            # passes, PLUS their own dedicated breakdown table below (same
            # pattern as Document/Pass Processing Time). Measured as
            # create_date -> the completion log entry's event_date, since HR
            # Requests don't have a separate submitted/issued event pair the
            # way renewals/applications do — the whole request lifecycle IS
            # the thing being timed. ─────────────────────────────────────────
            def hr_calc_days(requests, end_state):
                days_list = []
                for req in requests.sudo():
                    if req.state != end_state:
                        continue
                    completed_log = req.history_ids.filtered(
                        lambda l: l.event_type in ('completed', 'closed'))
                    if completed_log:
                        latest = max(completed_log, key=lambda l: l.event_date)
                        delta = (latest.event_date - req.create_date).days
                        if delta >= 0:
                            days_list.append(delta)
                return days_list

            all_residency = self.env['field.pass.hr.residency.request'].sudo().search([])
            residency_days = hr_calc_days(all_residency, 'completed')
            all_visa = self.env['field.pass.hr.visa.request'].sudo().search([])
            visa_days = hr_calc_days(all_visa, 'closed')
            hr_days = residency_days + visa_days

            all_pairs = doc_pairs + pass_pairs
            all_days = [d for d, _ in all_pairs] + hr_days
            doc_days = [d for d, _ in doc_pairs]
            pass_days = [d for d, _ in pass_pairs]

            rec.stat_total_completed = len(all_pairs) + len(hr_days)
            # Currently Processing — confirmed: folds in in-flight HR
            # Requests (not draft, not completed/closed) and Company
            # Documents currently needing attention (warning/expired) on top
            # of the existing submitted-but-not-issued documents/passes.
            hr_residency_inflight = self.env['field.pass.hr.residency.request'].sudo().search_count(
                [('state', 'not in', ('draft', 'completed', 'closed'))])
            hr_visa_inflight = self.env['field.pass.hr.visa.request'].sudo().search_count(
                [('state', 'not in', ('draft', 'closed', 'rejected_closed'))])
            company_doc_issues = self.env['field.pass.company.document'].sudo().search_count(
                [('status', 'in', ('warning', 'expired')), ('active', '=', True)])
            rec.stat_processing = (len(submitted_r) + len(submitted_a)
                                   + hr_residency_inflight + hr_visa_inflight + company_doc_issues)
            rec.stat_avg_doc_days  = round(sum(doc_days)/len(doc_days), 1) if doc_days else 0.0
            rec.stat_avg_pass_days = round(sum(pass_days)/len(pass_days), 1) if pass_days else 0.0
            rec.stat_fastest_days  = min(all_days) if all_days else 0
            rec.stat_slowest_days  = max(all_days) if all_days else 0

            # HR stats by request type
            hr_lines = []
            if residency_days:
                hr_lines.append(self.env['field.pass.stat.line'].create({
                    'label': 'Residency Transfer',
                    'avg_days': round(sum(residency_days)/len(residency_days), 1),
                    'count': len(residency_days),
                    'fastest': min(residency_days),
                    'slowest': max(residency_days),
                }))
            if visa_days:
                hr_lines.append(self.env['field.pass.stat.line'].create({
                    'label': 'Work Visa',
                    'avg_days': round(sum(visa_days)/len(visa_days), 1),
                    'count': len(visa_days),
                    'fastest': min(visa_days),
                    'slowest': max(visa_days),
                }))
            rec.stat_hr_line_ids = [(6, 0, [l.id for l in hr_lines])]

            # Doc stats by document_type
            from collections import defaultdict
            doc_by_type = defaultdict(list)
            for days, issued in doc_pairs:
                doc_by_type[issued.document_type].append(days)

            doc_labels = {
                'passport': 'Passport', 'residency': 'Residency', 'civil_id': 'Civil ID',
                'driving_license': 'Driving License', 'driving_hse': 'Driving HSE',
                'driving_authority': 'Driving Authority',
                'registration': 'Registration',
                'third_party': '3rd Party Inspection', 'clearance': 'Clearance Certificate',
            }
            doc_lines = []
            for dtype, days_list in sorted(doc_by_type.items(), key=lambda x: -sum(x[1])/len(x[1])):
                doc_lines.append(self.env['field.pass.stat.line'].create({
                    'label': doc_labels.get(dtype, dtype),
                    'avg_days': round(sum(days_list)/len(days_list), 1),
                    'count': len(days_list),
                    'fastest': min(days_list),
                    'slowest': max(days_list),
                }))
            rec.stat_doc_line_ids = [(6, 0, [l.id for l in doc_lines])]

            # Pass stats by pass_type
            pass_by_type = defaultdict(list)
            for days, issued in pass_pairs:
                pass_by_type[issued.pass_type].append(days)

            pass_labels = {
                'KOC': 'KOC Field Pass', 'RATQA_ABDALLY': 'RATQA & Abdally',
                'WAFRA': 'Wafra Pass', 'FAWARES': 'Fawares Pass', 'TEMP': 'Temp Pass',
                'PTW': 'PTW', 'KOC_LAPTOP': 'KOC Laptop Pass',
            }
            pass_lines = []
            for ptype, days_list in sorted(pass_by_type.items(), key=lambda x: -sum(x[1])/len(x[1])):
                pass_lines.append(self.env['field.pass.stat.line'].create({
                    'label': pass_labels.get(ptype, ptype),
                    'avg_days': round(sum(days_list)/len(days_list), 1),
                    'count': len(days_list),
                    'fastest': min(days_list),
                    'slowest': max(days_list),
                }))
            rec.stat_pass_line_ids = [(6, 0, [l.id for l in pass_lines])]

            # Nationality stats
            nat_days = defaultdict(list)
            for days, issued in doc_pairs:
                if issued.employee_id and issued.employee_id.nationality:
                    nat_days[issued.employee_id.nationality].append(days)
            nat_lines = []
            for nat, days_list in sorted(nat_days.items(), key=lambda x: -sum(x[1])/len(x[1])):
                nat_lines.append(self.env['field.pass.stat.line'].create({
                    'label': nat,
                    'avg_days': round(sum(days_list)/len(days_list), 1),
                    'count': len(days_list),
                    'fastest': min(days_list),
                    'slowest': max(days_list),
                }))
            rec.stat_nat_line_ids = [(6, 0, [l.id for l in nat_lines])]

    def _rebuild_dept_lines(self):
        """Rebuild department breakdown lines."""
        self.ensure_one()
        PASS_FIELDS = ['pass_koc_status', 'pass_ratqa_status',
                       'pass_wafra_status', 'pass_fawares_status']

        cid = self.company_id.id or self.env.company.id
        emp_domain = [('company_id', '=', cid), ('active', '=', True)]
        veh_domain = [('company_id', '=', cid), ('active', '=', True)]
        if self.department_id:
            emp_domain.append(('department_id', '=', self.department_id.id))
            veh_domain.append(('department_id', '=', self.department_id.id))

        emps = self._search_scoped('field.pass.employee', emp_domain)
        vehs = self._search_scoped('field.pass.vehicle', veh_domain)
        self.department_line_ids.unlink()

        if self.department_id:
            depts = self.department_id
        else:
            dept_ids = set(emps.mapped('department_id').ids + vehs.mapped('department_id').ids)
            depts = self.env['hr.department'].sudo().browse(dept_ids)

        def emp_pass_has(e, statuses):
            return any(getattr(e, f) in statuses for f in PASS_FIELDS)

        def veh_pass_has(v, statuses):
            return any(getattr(v, f) in statuses for f in PASS_FIELDS)

        def worst(records, status_field):
            statuses = [getattr(r, status_field) for r in records]
            if 'expired' in statuses or 'missing' in statuses:
                return 'danger'
            if 'warning' in statuses or 'temp_warning' in statuses:
                return 'warning'
            if any(s in ['valid', 'temp_active'] for s in statuses):
                return 'ok'
            return 'na'

        def pass_worst(records):
            worst_val = 'na'
            for r in records:
                for f in PASS_FIELDS:
                    s = getattr(r, f)
                    if s in ['expired', 'missing']:
                        return 'danger'
                    if s in ['warning', 'temp_warning']:
                        worst_val = 'warning'
                    elif s in ['valid', 'temp_active'] and worst_val == 'na':
                        worst_val = 'ok'
            return worst_val

        lines = []
        for dept in depts.sorted('name'):
            dept_emps = emps.filtered(lambda e: e.department_id.id == dept.id)
            dept_vehs = vehs.filtered(lambda v: v.department_id.id == dept.id)
            lines.append({
                'dashboard_id': self.id,
                'department_id': dept.id,
                'emp_count': len(dept_emps),
                'veh_count': len(dept_vehs),
                'emp_doc_status': worst(dept_emps, 'overall_doc_status'),
                'emp_doc_expired': len(dept_emps.filtered(lambda e: e.overall_doc_status == 'expired')),
                'emp_doc_warning': len(dept_emps.filtered(lambda e: e.overall_doc_status == 'warning')),
                'emp_pass_status': pass_worst(dept_emps),
                'emp_pass_missing': len(dept_emps.filtered(lambda e: emp_pass_has(e, ['missing']))),
                'emp_pass_expired': len(dept_emps.filtered(lambda e: emp_pass_has(e, ['expired']))),
                'veh_doc_status': worst(dept_vehs, 'overall_doc_status'),
                'veh_doc_expired': len(dept_vehs.filtered(lambda v: v.overall_doc_status == 'expired')),
                'veh_doc_warning': len(dept_vehs.filtered(lambda v: v.overall_doc_status == 'warning')),
                'veh_pass_status': pass_worst(dept_vehs),
                'veh_pass_missing': len(dept_vehs.filtered(lambda v: veh_pass_has(v, ['missing']))),
                'veh_pass_expired': len(dept_vehs.filtered(lambda v: veh_pass_has(v, ['expired']))),
                'veh_pass_warning': len(dept_vehs.filtered(lambda v: veh_pass_has(v, ['warning', 'temp_warning']))),
                'emp_pass_warning': len(dept_emps.filtered(lambda e: emp_pass_has(e, ['warning', 'temp_warning']))),
                'emp_field_count':  len(dept_emps.filtered(lambda e: e.job_type == 'Field')),
                'emp_driver_count': len(dept_emps.filtered(lambda e: e.job_type == 'Driver')),
                'emp_office_count': len(dept_emps.filtered(lambda e: e.job_type == 'Office')),
            })
        if lines:
            self.env['field.pass.dashboard.dept'].create(lines)

    def _rebuild_company_doc_lines(self):
        """
        Simple breakdown, confirmed design: company name + counts of ALL its
        documents (main entries AND sub-documents together — a sub-document
        expiring matters just as much as a main one) by valid/warning/
        expired. No department/company_id filtering — field.pass.company is
        a standalone model, not tied to res.company multi-company setup.

        Runs entirely via sudo() — Viewer-tier users no longer have direct
        access to field.pass.company/field.pass.company.document (confirmed:
        Company data is Admin/Manager only, including the dashboard tab),
        but the Dashboard itself opens for everyone, and this rebuild runs
        unconditionally as part of that. Without sudo() here, a Viewer
        opening the Dashboard would crash on this step, not just see an
        empty/hidden tab as intended.
        """
        self.ensure_one()
        self.sudo().company_line_ids.unlink()

        companies = self.env['field.pass.company'].sudo().search([('active', '=', True)])
        lines = []
        for comp in companies.sorted('name'):
            docs = comp.document_ids.filtered('active')
            lines.append({
                'dashboard_id': self.id,
                'company_ref_id': comp.id,
                'company_name': comp.name,
                'doc_valid': len(docs.filtered(lambda d: d.status == 'valid')),
                'doc_warning': len(docs.filtered(lambda d: d.status == 'warning')),
                'doc_expired': len(docs.filtered(lambda d: d.status == 'expired')),
                'doc_total': len(docs),
            })
        if lines:
            self.env['field.pass.dashboard.company'].sudo().create(lines)

    @api.model
    def get_dashboard(self):
        """Get or create the singleton dashboard record."""
        self._check_ops_department_assignment()
        dashboard = self.search([('company_id', '=', self.env.company.id)], limit=1)
        if not dashboard:
            dashboard = self.create({'company_id': self.env.company.id})
        dashboard._rebuild_dept_lines()
        dashboard._rebuild_company_doc_lines()
        return dashboard

    def _check_ops_department_assignment(self):
        """
        Confirmed design: an OPS user who isn't assigned to ANY department
        at all shouldn't see a working Dashboard — an empty/blank one is
        confusing, not helpful. Only applies if OPS is the user's ONLY
        relevant track here — someone who is ALSO GRO/HR/Super Admin still
        sees the Dashboard normally through that other access, since this
        check is specifically about "OPS with nothing assigned", not about
        blocking anyone who happens to hold an OPS role incidentally.
        """
        user = self.env.user
        is_ops = user.has_group('field_pass_tracker.group_fp_ops_viewer')
        if not is_ops:
            return
        has_other_track = (
            user.has_group('field_pass_tracker.group_fp_viewer')
            or user.has_group('field_pass_tracker.group_fp_hr_viewer')
            or user.has_group('field_pass_tracker.group_fp_super_admin')
        )
        if has_other_track:
            return
        assigned = self.env['hr.department'].sudo().search([
            '|', '|', '|', '|', '|',
            ('ops_manager_id', '=', user.id),
            ('ops_admin1_id', '=', user.id),
            ('ops_admin2_id', '=', user.id),
            ('ops_viewer1_id', '=', user.id),
            ('ops_viewer2_id', '=', user.id),
            ('ops_viewer3_id', '=', user.id),
        ], limit=1)
        if not assigned:
            raise UserError(
                'You are not currently assigned to any department. '
                'Please contact your administrator to be assigned before '
                'the Dashboard becomes available.'
            )

    def action_refresh(self):
        """Apply department filter and rebuild."""
        self._rebuild_dept_lines()
        self._rebuild_company_doc_lines()
        # Force recompute of non-stored fields
        self.invalidate_recordset()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Dashboard',
            'res_model': 'field.pass.dashboard',
            'view_mode': 'form',
            'target': 'current',
            'res_id': self.id,
        }

    # ── ACTIONS ───────────────────────────────────────────────────────────────
    def _emp_action(self, name, domain):
        if self.department_id:
            domain.append(('department_id', '=', self.department_id.id))
        tree_view = self.env.ref(
            'field_pass_tracker.view_fp_employee_pass_status_tree', False)
        views = [(tree_view.id, 'tree')] if tree_view else [(False, 'tree')]
        return {'type': 'ir.actions.act_window', 'name': name,
                'res_model': 'field.pass.employee',
                'view_mode': 'tree,form',
                'views': views + [(False, 'form')],
                'domain': domain + [('active', '=', True)]}

    def _emp_doc_action(self, name, domain):
        if self.department_id:
            domain.append(('department_id', '=', self.department_id.id))
        tree_view = self.env.ref(
            'field_pass_tracker.view_fp_employee_doc_status_tree', False)
        views = [(tree_view.id, 'tree')] if tree_view else [(False, 'tree')]
        return {'type': 'ir.actions.act_window', 'name': name,
                'res_model': 'field.pass.employee',
                'view_mode': 'tree,form',
                'views': views + [(False, 'form')],
                'domain': domain + [('active', '=', True)]}

    def _veh_action(self, name, domain):
        if self.department_id:
            domain.append(('department_id', '=', self.department_id.id))
        tree_view = self.env.ref(
            'field_pass_tracker.view_fp_vehicle_pass_status_tree', False)
        views = [(tree_view.id, 'tree')] if tree_view else [(False, 'tree')]
        return {'type': 'ir.actions.act_window', 'name': name,
                'res_model': 'field.pass.vehicle',
                'view_mode': 'tree,form',
                'views': views + [(False, 'form')],
                'domain': domain + [('active', '=', True)]}

    def _veh_doc_action(self, name, domain):
        if self.department_id:
            domain.append(('department_id', '=', self.department_id.id))
        tree_view = self.env.ref(
            'field_pass_tracker.view_fp_vehicle_doc_status_tree', False)
        views = [(tree_view.id, 'tree')] if tree_view else [(False, 'tree')]
        return {'type': 'ir.actions.act_window', 'name': name,
                'res_model': 'field.pass.vehicle',
                'view_mode': 'tree,form',
                'views': views + [(False, 'form')],
                'domain': domain + [('active', '=', True)]}

    def action_emp_doc_expired(self):
        return self._emp_doc_action('Employees — Expired Documents', [('overall_doc_status', '=', 'expired')])
    def action_emp_doc_warning(self):
        return self._emp_doc_action('Employees — Expiring Documents', [('overall_doc_status', '=', 'warning')])
    def action_emp_pass_expired(self):
        return self._emp_action('Employees — Expired Passes', ['|', '|', '|',
            ('pass_koc_status', '=', 'expired'),
            ('pass_ratqa_status', '=', 'expired'),
            ('pass_wafra_status', '=', 'expired'),
            ('pass_fawares_status', '=', 'expired')])
    def action_emp_pass_warning(self):
        return self._emp_action('Employees — Expiring Passes', ['|', '|', '|',
            ('pass_koc_status', 'in', ['warning', 'temp_warning']),
            ('pass_ratqa_status', 'in', ['warning', 'temp_warning']),
            ('pass_wafra_status', 'in', ['warning', 'temp_warning']),
            ('pass_fawares_status', 'in', ['warning', 'temp_warning'])])
    def action_emp_pass_missing(self):
        return self._emp_action('Employees — Missing Passes', ['|', '|', '|',
            ('pass_koc_status', '=', 'missing'),
            ('pass_ratqa_status', '=', 'missing'),
            ('pass_wafra_status', '=', 'missing'),
            ('pass_fawares_status', '=', 'missing')])
    def action_emp_pass_temp(self):
        return self._emp_action('Employees — On Temp Pass', [
            '|', '|', '|',
            ('pass_koc_status', 'in', ['temp_active', 'temp_warning']),
            ('pass_ratqa_status', 'in', ['temp_active', 'temp_warning']),
            ('pass_wafra_status', 'in', ['temp_active', 'temp_warning']),
            ('pass_fawares_status', 'in', ['temp_active', 'temp_warning']),
        ])
    def action_veh_doc_expired(self):
        return self._veh_doc_action('Vehicles — Expired Documents', [('overall_doc_status', '=', 'expired')])
    def action_veh_doc_warning(self):
        return self._veh_doc_action('Vehicles — Expiring Documents', [('overall_doc_status', '=', 'warning')])
    def action_veh_pass_expired(self):
        return self._veh_action('Vehicles — Expired Passes', ['|', '|', '|',
            ('pass_koc_status', '=', 'expired'),
            ('pass_ratqa_status', '=', 'expired'),
            ('pass_wafra_status', '=', 'expired'),
            ('pass_fawares_status', '=', 'expired')])
    def action_veh_pass_warning(self):
        return self._veh_action('Vehicles — Expiring Passes', ['|', '|', '|',
            ('pass_koc_status', 'in', ['warning', 'temp_warning']),
            ('pass_ratqa_status', 'in', ['warning', 'temp_warning']),
            ('pass_wafra_status', 'in', ['warning', 'temp_warning']),
            ('pass_fawares_status', 'in', ['warning', 'temp_warning'])])
    def action_veh_pass_missing(self):
        return self._veh_action('Vehicles — Missing Passes', ['|', '|', '|',
            ('pass_koc_status', '=', 'missing'),
            ('pass_ratqa_status', '=', 'missing'),
            ('pass_wafra_status', '=', 'missing'),
            ('pass_fawares_status', '=', 'missing')])
    def action_veh_pass_temp(self):
        return self._veh_action('Vehicles — On Temp Pass', [
            '|', '|', '|',
            ('pass_koc_status', 'in', ['temp_active', 'temp_warning']),
            ('pass_ratqa_status', 'in', ['temp_active', 'temp_warning']),
            ('pass_wafra_status', 'in', ['temp_active', 'temp_warning']),
            ('pass_fawares_status', 'in', ['temp_active', 'temp_warning']),
        ])



    # ── Status Fields ─────────────────────────────────────────────────────────
    emp_pass_status = fields.Char(compute='_compute_stats', store=False)
    veh_pass_status = fields.Char(compute='_compute_stats', store=False)
    emp_doc_status  = fields.Char(compute='_compute_stats', store=False)
    veh_doc_status  = fields.Char(compute='_compute_stats', store=False)


    # ── Statistics Fields ─────────────────────────────────────────────────────
    stat_avg_doc_days   = fields.Float(compute='_compute_stats', store=False, string='Avg Doc Days')
    stat_avg_pass_days  = fields.Float(compute='_compute_stats', store=False, string='Avg Pass Days')
    stat_fastest_days   = fields.Integer(compute='_compute_stats', store=False, string='Fastest (days)')
    stat_slowest_days   = fields.Integer(compute='_compute_stats', store=False, string='Slowest (days)')
    stat_total_completed = fields.Integer(compute='_compute_stats', store=False, string='Total Completed')
    stat_processing     = fields.Integer(compute='_compute_stats', store=False, string='Processing')

    # Statistics detail lines
    stat_doc_line_ids = fields.Many2many(
        'field.pass.stat.line', 'fp_dash_stat_doc_rel', 'dash_id', 'line_id',
        compute='_compute_stats', store=False, string='Doc Stats')
    stat_nat_line_ids = fields.Many2many(
        'field.pass.stat.line', 'fp_dash_stat_nat_rel', 'dash_id', 'line_id',
        compute='_compute_stats', store=False, string='Nationality Stats')
    stat_pass_line_ids = fields.Many2many(
        'field.pass.stat.line', 'fp_dash_stat_pass_rel', 'dash_id', 'line_id',
        compute='_compute_stats', store=False, string='Pass Stats')
    stat_hr_line_ids = fields.Many2many(
        'field.pass.stat.line', 'fp_dash_stat_hr_rel', 'dash_id', 'line_id',
        compute='_compute_stats', store=False, string='HR Request Stats')

class FieldPassDashboardDept(models.Model):
    _name = 'field.pass.dashboard.dept'
    _description = 'Field Pass Dashboard Department Line'
    _order = 'department_id'

    dashboard_id    = fields.Many2one('field.pass.dashboard', ondelete='cascade')
    department_id   = fields.Many2one('hr.department', string='Department')
    emp_count       = fields.Integer(string='Employees')
    veh_count       = fields.Integer(string='Vehicles')
    emp_doc_status  = fields.Selection([('ok','OK'),('warning','Warning'),('danger','Issues'),('na','N/A')])
    emp_doc_expired = fields.Integer()
    emp_doc_warning = fields.Integer()
    emp_pass_status = fields.Selection([('ok','OK'),('warning','Warning'),('danger','Issues'),('na','N/A')])
    emp_pass_missing= fields.Integer()
    emp_pass_expired= fields.Integer()
    veh_doc_status  = fields.Selection([('ok','OK'),('warning','Warning'),('danger','Issues'),('na','N/A')])
    veh_doc_expired = fields.Integer()
    veh_doc_warning = fields.Integer()
    veh_pass_status = fields.Selection([('ok','OK'),('warning','Warning'),('danger','Issues'),('na','N/A')])
    veh_pass_missing= fields.Integer()
    veh_pass_expired= fields.Integer()
    veh_pass_warning= fields.Integer()
    emp_pass_warning= fields.Integer()
    emp_field_count = fields.Integer()
    emp_driver_count= fields.Integer()
    emp_office_count= fields.Integer()


class FieldPassDashboardCompany(models.Model):
    _name = 'field.pass.dashboard.company'
    _description = 'Field Pass Dashboard Company Document Line'
    _order = 'company_name'

    dashboard_id = fields.Many2one('field.pass.dashboard', ondelete='cascade')
    company_ref_id = fields.Many2one('field.pass.company', string='Company')
    company_name = fields.Char(string='Company - الشركة')
    doc_valid = fields.Integer(string='Valid - ساري')
    doc_warning = fields.Integer(string='Warning - قريب الانتهاء')
    doc_expired = fields.Integer(string='Expired - منتهي')
    doc_total = fields.Integer(string='Total - الإجمالي')


class FieldPassStatLine(models.TransientModel):
    _name = 'field.pass.stat.line'
    _description = 'Statistics Line'

    label    = fields.Char(string='Category')
    avg_days = fields.Float(string='Avg Days')
    count    = fields.Integer(string='Count')
    fastest  = fields.Integer(string='Fastest')
    slowest  = fields.Integer(string='Slowest')

