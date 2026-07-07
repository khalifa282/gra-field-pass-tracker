# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError

PASS_TYPES = [
    ('KOC', 'KOC Field Pass - تصاريح الكي او سي'),
    ('RATQA_ABDALLY', 'RATQA & Abdally - تصريح الرتقة والعبدلي'),
    ('WAFRA', 'Wafra Pass - تصريح الوفرة'),
    ('FAWARES', 'Fawares Pass - تصريح الفوارس'),
    ('TEMP', 'Temp Field Pass - تصريح مؤقت'),
]


class FieldPassApplicationWizard(models.TransientModel):
    _name = 'field.pass.application.wizard'
    _description = 'Pass Application Wizard'
    _rec_name = 'display_name'

    display_name = fields.Char(compute='_compute_display_name', store=True)

    @api.depends('pass_type', 'employee_id', 'vehicle_id')
    def _compute_display_name(self):
        pt_map = dict(PASS_TYPES)
        for r in self:
            pt = pt_map.get(r.pass_type, r.pass_type or 'Pass Application')
            entity = r.employee_id.name if r.employee_id else (
                r.vehicle_id.plate_number if r.vehicle_id else '')
            r.display_name = f'{pt} - {entity}' if entity else pt

    # Step 1
    entity_type = fields.Selection([
        ('employee', 'Employee - موظفين'),
        ('vehicle', 'Vehicle - مركبات'),
    ], string='Field Pass Type - تصريح افراد او مركبات')

    # Step 2
    employee_id = fields.Many2one('field.pass.employee',
                                   string='Employee Name - اسم الموظف')
    vehicle_id = fields.Many2one('field.pass.vehicle',
                                  string='Vehicle Number - رقم المركبة')

    # Step 3
    pass_type = fields.Selection(PASS_TYPES,
                                  string='Pass Type - نوع التصريح')

    # Step 4 - Employee documents (related, no store needed)
    doc_passport = fields.Binary(related='employee_id.attachment_passport', readonly=True)
    doc_passport_name = fields.Char(related='employee_id.attachment_passport_name', readonly=True)
    doc_residency = fields.Binary(related='employee_id.attachment_residency', readonly=True)
    doc_residency_name = fields.Char(related='employee_id.attachment_residency_name', readonly=True)
    doc_civil_id = fields.Binary(related='employee_id.attachment_civil_id', readonly=True)
    doc_civil_id_name = fields.Char(related='employee_id.attachment_civil_id_name', readonly=True)
    doc_driving_license = fields.Binary(related='employee_id.attachment_driving_license', readonly=True)
    doc_driving_license_name = fields.Char(related='employee_id.attachment_driving_license_name', readonly=True)
    doc_ptw = fields.Binary(related='employee_id.attachment_ptw', readonly=True)
    doc_ptw_name = fields.Char(related='employee_id.attachment_ptw_name', readonly=True)
    doc_koc_laptop = fields.Binary(related='employee_id.attachment_koc_laptop', readonly=True)
    doc_koc_laptop_name = fields.Char(related='employee_id.attachment_koc_laptop_name', readonly=True)

    # Step 4 - Vehicle documents
    doc_registration = fields.Binary(related='vehicle_id.attachment_registration', readonly=True)
    doc_registration_name = fields.Char(related='vehicle_id.attachment_registration_name', readonly=True)
    doc_third_party = fields.Binary(related='vehicle_id.attachment_third_party', readonly=True)
    doc_third_party_name = fields.Char(related='vehicle_id.attachment_third_party_name', readonly=True)
    doc_clearance = fields.Binary(related='vehicle_id.attachment_clearance', readonly=True)
    doc_clearance_name = fields.Char(related='vehicle_id.attachment_clearance_name', readonly=True)

    # History - stored Many2many using relation table
    has_open_submission = fields.Boolean(
        compute='_compute_status', store=True)
    history_ids = fields.Many2many(
        'field.pass.application',
        'fp_app_wiz_hist_rel',
        'wizard_id', 'app_id',
        string='History',
        compute='_compute_status', store=True,
    )

    @api.depends('pass_type', 'employee_id', 'vehicle_id', 'entity_type')
    def _compute_status(self):
        for r in self:
            if not r.pass_type:
                r.has_open_submission = False
                r.history_ids = [(5, 0, 0)]
                continue
            entity = r.employee_id if r.entity_type == 'employee' else r.vehicle_id
            if not entity:
                r.has_open_submission = False
                r.history_ids = [(5, 0, 0)]
                continue
            domain = [('pass_type', '=', r.pass_type)]
            if r.entity_type == 'employee':
                domain.append(('employee_id', '=', r.employee_id.id))
            else:
                domain.append(('vehicle_id', '=', r.vehicle_id.id))
            apps = self.env['field.pass.application'].search(
                domain, order='event_date desc')
            r.history_ids = [(6, 0, apps.ids)]
            latest = apps[0] if apps else False
            r.has_open_submission = bool(latest and latest.state == 'submitted')

    def _get_entity_domain(self):
        if self.entity_type == 'employee' and self.employee_id:
            return [('employee_id', '=', self.employee_id.id)]
        elif self.entity_type == 'vehicle' and self.vehicle_id:
            return [('vehicle_id', '=', self.vehicle_id.id)]
        return []

    def _new_wizard(self):
        new = self.env['field.pass.application.wizard'].create({
            'entity_type': self.entity_type,
            'pass_type': self.pass_type,
            'employee_id': self.employee_id.id if self.employee_id else False,
            'vehicle_id': self.vehicle_id.id if self.vehicle_id else False,
        })
        return {
            'type': 'ir.actions.act_window',
            'name': 'Pass Applications - معاملات التصاريح',
            'res_model': 'field.pass.application.wizard',
            'view_mode': 'form',
            'target': 'inline',
            'res_id': new.id,
        }

    def action_submit_application(self):
        self.ensure_one()
        if not self.pass_type:
            raise ValidationError('Please select a pass type.')
        domain = self._get_entity_domain()
        if not domain:
            raise ValidationError('Please select an employee or vehicle.')
        # Check latest event - only block if latest is submitted
        latest = self.env['field.pass.application'].search(
            [('pass_type', '=', self.pass_type)] + domain,
            order='event_date desc', limit=1)
        if latest and latest.state == 'submitted':
            raise ValidationError(
                'There is already an open submission. Please issue or reject it first.')
        # Prerequisite: Wafra/Fawares require WJO HSE Training
        if self.pass_type in ('WAFRA', 'FAWARES') and self.entity_type == 'employee':
            if not self.employee_id.wjo_hse_training_attended:
                raise ValidationError(
                    f'Cannot submit {self.pass_type} pass application for '
                    f'"{self.employee_id.name}". '
                    f'WJO HSE Training must be attended first.'
                )

        vals = {
            'pass_type': self.pass_type,
            'event_by': self.env.user.id,
            'state': 'submitted',
        }
        if self.entity_type == 'employee':
            vals['employee_id'] = self.employee_id.id
        else:
            vals['vehicle_id'] = self.vehicle_id.id
        self.env['field.pass.application'].create(vals)
        return self._new_wizard()

    def action_open_reject_wizard(self):
        self.ensure_one()
        domain = self._get_entity_domain()
        # Find latest submitted event
        all_apps = self.env['field.pass.application'].search(
            [('pass_type', '=', self.pass_type)] + domain,
            order='event_date desc', limit=1)
        latest = all_apps if all_apps and all_apps.state == 'submitted' else False
        if not latest:
            raise ValidationError('No open submission found.')
        return {
            'type': 'ir.actions.act_window',
            'name': 'Reject Application - رفض الطلب',
            'res_model': 'field.pass.application.reject.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_entity_type': self.entity_type,
                'default_pass_type': self.pass_type,
                'default_employee_id': self.employee_id.id if self.employee_id else False,
                'default_vehicle_id': self.vehicle_id.id if self.vehicle_id else False,
            },
        }

    def action_open_issue_wizard(self):
        self.ensure_one()
        domain = self._get_entity_domain()
        all_apps = self.env['field.pass.application'].search(
            [('pass_type', '=', self.pass_type)] + domain,
            order='event_date desc', limit=1)
        latest = all_apps if all_apps and all_apps.state == 'submitted' else False
        if not latest:
            raise ValidationError('No open submission found.')
        return {
            'type': 'ir.actions.act_window',
            'name': 'Issue Pass - إصدار التصريح',
            'res_model': 'field.pass.application.issue.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_entity_type': self.entity_type,
                'default_pass_type': self.pass_type,
                'default_employee_id': self.employee_id.id if self.employee_id else False,
                'default_vehicle_id': self.vehicle_id.id if self.vehicle_id else False,
            },
        }


class FieldPassApplicationRejectWizard(models.TransientModel):
    _name = 'field.pass.application.reject.wizard'
    _description = 'Reject Application Wizard'

    entity_type = fields.Char()
    pass_type = fields.Char()
    employee_id = fields.Many2one('field.pass.employee')
    vehicle_id = fields.Many2one('field.pass.vehicle')
    rejection_reason = fields.Text(
        string='Rejection Reason - سبب الرفض', required=True)

    def action_confirm(self):
        vals = {
            'pass_type': self.pass_type,
            'state': 'rejected',
            'event_by': self.env.user.id,
            'rejection_reason': self.rejection_reason,
        }
        if self.employee_id:
            vals['employee_id'] = self.employee_id.id
        else:
            vals['vehicle_id'] = self.vehicle_id.id
        self.env['field.pass.application'].create(vals)
        new = self.env['field.pass.application.wizard'].create({
            'entity_type': self.entity_type or False,
            'pass_type': self.pass_type or False,
            'employee_id': self.employee_id.id if self.employee_id else False,
            'vehicle_id': self.vehicle_id.id if self.vehicle_id else False,
        })
        new._compute_status()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Pass Applications',
            'res_model': 'field.pass.application.wizard',
            'view_mode': 'form',
            'target': 'inline',
            'res_id': new.id,
        }


class FieldPassApplicationIssueWizard(models.TransientModel):
    _name = 'field.pass.application.issue.wizard'
    _description = 'Issue Pass Wizard'

    entity_type = fields.Char()
    pass_type = fields.Char()
    employee_id = fields.Many2one('field.pass.employee')
    vehicle_id = fields.Many2one('field.pass.vehicle')
    expiry_date = fields.Date(
        string='New Expiry Date - تاريخ الانتهاء الجديد', required=True)
    attachment_pass = fields.Binary(
        string='Pass Document - وثيقة التصريح', attachment=True)
    attachment_pass_name = fields.Char(string='Pass Document Filename')

    def action_confirm(self):
        vals = {
            'pass_type': self.pass_type,
            'state': 'issued',
            'event_by': self.env.user.id,
            'expiry_date': self.expiry_date,
            'attachment_pass': self.attachment_pass,
            'attachment_pass_name': self.attachment_pass_name,
        }
        if self.employee_id:
            vals['employee_id'] = self.employee_id.id
        else:
            vals['vehicle_id'] = self.vehicle_id.id
        app = self.env['field.pass.application'].create(vals)
        app.action_update_pass_record()
        new = self.env['field.pass.application.wizard'].create({
            'entity_type': self.entity_type or False,
            'pass_type': self.pass_type or False,
            'employee_id': self.employee_id.id if self.employee_id else False,
            'vehicle_id': self.vehicle_id.id if self.vehicle_id else False,
        })
        return {
            'type': 'ir.actions.act_window',
            'name': 'Pass Applications',
            'res_model': 'field.pass.application.wizard',
            'view_mode': 'form',
            'target': 'inline',
            'res_id': new.id,
        }
