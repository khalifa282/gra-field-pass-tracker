# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import date


PASS_TYPES = [
    ('KOC',           'KOC Field Pass'),
    ('RATQA_ABDALLY', 'RATQA & Abdally GP'),
    ('WAFRA',         'Wafra Field Pass'),
    ('FAWARES',       'Fawares Field Pass'),
    ('TEMP',          'Temp Field Pass'),
]

APP_STATUS = [
    ('no',            'No Application'),
    ('under_process', 'Under Process'),
    ('yes',           'Active / Issued'),
]

DOC_KEY_MAP = {
    'KOC': 'fp_koc', 'RATQA_ABDALLY': 'fp_ratqa_abdally',
    'WAFRA': 'fp_wafra', 'FAWARES': 'fp_fawares', 'TEMP': 'fp_temp',
}

# Maps department requirement field ÃƒÂ¢Ã¢â‚¬Â Ã¢â‚¬â„¢ pass type
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
                    f'Cannot add {dict(PASS_TYPES).get(r.pass_type)} Ã¢â‚¬â€ '
                    f'department "{dept.name}" is not a Kuwait Oil Company client.'
                )
            if r.pass_type in wjo_types and not dept.fp_client_wjo:
                raise ValidationError(
                    f'Cannot add {dict(PASS_TYPES).get(r.pass_type)} Ã¢â‚¬â€ '
                    f'department "{dept.name}" is not a Wafra Joint Operations client.'
                )
    
    def _check_wafra_fawares(self):
        for r in self:
            if r.employee_id and r.pass_type in ('WAFRA', 'FAWARES'):
                if not r.employee_id.wjo_hse_training_attended:
                    raise ValidationError(
                        f'Cannot create {dict(PASS_TYPES).get(r.pass_type)} pass for '
                        f'{r.employee_id.name}: WJO HSE Training not attended.'
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
            r.display_name = f'{entity} ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â {labels.get(r.pass_type, r.pass_type or "")}'

    @api.model
    def cron_send_expiry_alerts(self):
        pass
