# -*- coding: utf-8 -*-
from odoo import models, fields, api


class FieldPassDashboard(models.Model):
    # Use regular Model instead of TransientModel
    # This prevents Odoo garbage collector from deleting records
    _name = 'field.pass.dashboard'
    _description = 'Field Pass Dashboard'

    name = fields.Char(default='Dashboard', readonly=True)
    department_id = fields.Many2one('hr.department', string='Filter by Department')
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

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
    recent_renewal_ids = fields.Many2many(
        'field.pass.renewal', 'fp_dash_renewal_rel', 'dash_id', 'renewal_id',
        compute='_compute_all', store=True, string='Recent Renewals')
    recent_app_ids = fields.Many2many(
        'field.pass.application', 'fp_dash_app_rel', 'dash_id', 'app_id',
        compute='_compute_all', store=True, string='Recent Applications')

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

            emps = self.env['field.pass.employee'].search(emp_domain)
            vehs = self.env['field.pass.vehicle'].search(veh_domain)

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
            rec.renewal_submitted  = self.env['field.pass.renewal'].search_count([('event_type', '=', 'submitted')])
            rec.renewal_rejected   = self.env['field.pass.renewal'].search_count([('event_type', '=', 'rejected')])
            rec.pass_app_submitted = self.env['field.pass.application'].search_count([('state', '=', 'submitted')])
            rec.pass_app_rejected  = self.env['field.pass.application'].search_count([('state', '=', 'rejected')])

            # Recent activity (last 20)
            recent_renewals = self.env['field.pass.renewal'].search([], order='event_date desc', limit=20)
            rec.recent_renewal_ids = [(6, 0, recent_renewals.ids)]
            recent_apps = self.env['field.pass.application'].search([], order='event_date desc', limit=20)
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
            all_renewals = self.env['field.pass.renewal'].search([])
            submitted_r = all_renewals.filtered(lambda r: r.event_type == 'submitted')
            issued_r = all_renewals.filtered(lambda r: r.event_type == 'issued')
            doc_pairs = calc_days(submitted_r, issued_r)

            # Pass application stats
            all_apps = self.env['field.pass.application'].search([])
            submitted_a = all_apps.filtered(lambda a: a.state == 'submitted')
            issued_a = all_apps.filtered(lambda a: a.state == 'issued')
            pass_pairs = calc_days(submitted_a, issued_a)

            all_pairs = doc_pairs + pass_pairs
            all_days = [d for d, _ in all_pairs]
            doc_days = [d for d, _ in doc_pairs]
            pass_days = [d for d, _ in pass_pairs]

            rec.stat_total_completed = len(all_pairs)
            rec.stat_processing = len(submitted_r) + len(submitted_a)
            rec.stat_avg_doc_days  = round(sum(doc_days)/len(doc_days), 1) if doc_days else 0.0
            rec.stat_avg_pass_days = round(sum(pass_days)/len(pass_days), 1) if pass_days else 0.0
            rec.stat_fastest_days  = min(all_days) if all_days else 0
            rec.stat_slowest_days  = max(all_days) if all_days else 0

            # Doc stats by document_type
            from collections import defaultdict
            doc_by_type = defaultdict(list)
            for days, issued in doc_pairs:
                doc_by_type[issued.document_type].append(days)

            doc_labels = {
                'passport': 'Passport', 'residency': 'Residency', 'civil_id': 'Civil ID',
                'driving_license': 'Driving License', 'driving_hse': 'Driving HSE',
                'driving_authority': 'Driving Authority', 'ptw': 'PTW',
                'koc_laptop': 'KOC Laptop', 'registration': 'Registration',
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

        emps = self.env['field.pass.employee'].search(emp_domain)
        vehs = self.env['field.pass.vehicle'].search(veh_domain)

        # Delete old lines
        self.department_line_ids.unlink()

        if self.department_id:
            depts = self.department_id
        else:
            dept_ids = set(emps.mapped('department_id').ids + vehs.mapped('department_id').ids)
            depts = self.env['hr.department'].browse(dept_ids)

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

    @api.model
    def get_dashboard(self):
        """Get or create the singleton dashboard record."""
        dashboard = self.search([('company_id', '=', self.env.company.id)], limit=1)
        if not dashboard:
            dashboard = self.create({'company_id': self.env.company.id})
        dashboard._rebuild_dept_lines()
        return dashboard

    def action_refresh(self):
        """Apply department filter and rebuild."""
        self._rebuild_dept_lines()
        # Force recompute of non-stored fields
        self.invalidate_recordset()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Dashboard',
            'res_model': 'field.pass.dashboard',
            'view_mode': 'form',
            'target': 'inline',
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


class FieldPassStatLine(models.TransientModel):
    _name = 'field.pass.stat.line'
    _description = 'Statistics Line'

    label    = fields.Char(string='Category')
    avg_days = fields.Float(string='Avg Days')
    count    = fields.Integer(string='Count')
    fastest  = fields.Integer(string='Fastest')
    slowest  = fields.Integer(string='Slowest')

