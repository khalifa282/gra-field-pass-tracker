# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError

PASS_TYPES = [
    ('KOC', 'KOC Field Pass - تصاريح الكي او سي'),
    ('RATQA_ABDALLY', 'RATQA & Abdally - تصريح الرتقة والعبدلي'),
    ('WAFRA', 'Wafra Pass - تصريح الوفرة'),
    ('FAWARES', 'Fawares Pass - تصريح الفوارس'),
    ('TEMP', 'Temp Field Pass - تصريح مؤقت'),
    # MOVED from Document Renewal — same as field_pass.py and
    # field_pass_renewal_wizard.py's copies of this list (see note there
    # about this being duplicated 3x with no single source of truth).
    ('PTW', 'PTW - إذن فتح الآبار'),
    ('KOC_LAPTOP', 'KOC Laptop Pass - تصريح اللابتوب KOC'),
]


class FieldPassApplication(models.Model):
    """
    Event log — each row = one event.
    submitted → rejected → submitted → issued (each is a separate row)
    """
    _name = 'field.pass.application'
    _description = 'Field Pass Application Log'
    _order = 'event_date desc'
    _rec_name = 'display_name'

    display_name = fields.Char(compute='_compute_display_name', store=True)

    # Links
    employee_id = fields.Many2one('field.pass.employee', string='Employee - الموظف',
                                   ondelete='cascade')
    vehicle_id = fields.Many2one('field.pass.vehicle', string='Vehicle - المركبة',
                                  ondelete='cascade')
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    # Pass
    pass_type = fields.Selection(PASS_TYPES, string='Pass Type - نوع التصريح',
                                  required=True)

    # Event
    state = fields.Selection([
        ('submitted', 'Submitted - مقدم'),
        ('rejected', 'Rejected - مرفوض'),
        ('issued', 'Issued - صادر'),
    ], string='Status - الحالة', required=True, default='submitted')

    event_date = fields.Datetime(string='Date - التاريخ',
                                  default=fields.Datetime.now, readonly=True)
    event_by = fields.Many2one('res.users', string='By - بواسطة',
                                default=lambda self: self.env.user, readonly=True)

    # Rejection
    rejection_reason = fields.Text(string='Remarks - ملاحظات')

    # Issued
    expiry_date = fields.Date(string='Expiry Date - تاريخ الانتهاء')
    attachment_pass = fields.Binary(string='Pass Document - وثيقة التصريح', attachment=True)
    attachment_pass_name = fields.Char(string='Pass Document Filename')

    # Keep these for backward compatibility with existing views
    submission_date = fields.Datetime(related='event_date', store=True)
    submitted_by = fields.Many2one('res.users', related='event_by', store=True)
    decision_date = fields.Datetime(string='Decision Date', readonly=True)
    issued_date = fields.Datetime(string='Issued Date', readonly=True)
    decided_by = fields.Many2one('res.users', string='Decided By', readonly=True)
    issued_by = fields.Many2one('res.users', string='Issued By', readonly=True)

    @api.depends('employee_id', 'vehicle_id', 'pass_type', 'state')
    def _compute_display_name(self):
        for r in self:
            entity = r.employee_id.name if r.employee_id else (
                r.vehicle_id.plate_number if r.vehicle_id else '?')
            pt = dict(PASS_TYPES).get(r.pass_type, r.pass_type or '')
            st = dict([('submitted','Submitted'),('rejected','Rejected'),
                       ('issued','Issued')]).get(r.state, '')
            r.display_name = f'{entity} - {pt} [{st}]'

    @api.constrains('employee_id', 'vehicle_id')
    def _check_entity(self):
        for r in self:
            if r.employee_id and r.vehicle_id:
                raise ValidationError('Cannot link to both employee and vehicle.')
            if not r.employee_id and not r.vehicle_id:
                raise ValidationError('Must link to employee or vehicle.')

    def action_update_pass_record(self):
        """When issued - update the field.pass record."""
        self.ensure_one()
        if self.state != 'issued' or not self.expiry_date:
            return
        domain = [('pass_type', '=', self.pass_type), ('is_temp', '=', False)]
        if self.employee_id:
            domain.append(('employee_id', '=', self.employee_id.id))
        else:
            domain.append(('vehicle_id', '=', self.vehicle_id.id))
        existing = self.env['field.pass'].search(domain, limit=1)
        vals = {
            'pass_type': self.pass_type,
            'date_issued': fields.Date.today(),
            'date_expire': self.expiry_date,
            'application_status': 'yes',
            'attachment_pass': self.attachment_pass,
            'attachment_pass_name': self.attachment_pass_name,
        }
        if self.employee_id:
            vals['employee_id'] = self.employee_id.id
        else:
            vals['vehicle_id'] = self.vehicle_id.id
        if existing:
            existing.write(vals)
        else:
            self.env['field.pass'].create(vals)
