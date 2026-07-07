# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class FieldPassContract(models.Model):
    _name = 'field.pass.contract'
    _description = 'Field Pass Contract'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'contract_number asc'
    _rec_name = 'contract_number'

    contract_number = fields.Char(string='Contract Number', required=True, tracking=True)
    description = fields.Char(string='Description', tracking=True)
    department_id = fields.Many2one(
        'hr.department', string='Department', required=True,
        tracking=True, ondelete='restrict',
    )
    company_id = fields.Many2one(
        'res.company', string='Company', required=True,
        default=lambda self: self.env.company, tracking=True,
    )
    active = fields.Boolean(string='Active', default=True, tracking=True)

    employee_count = fields.Integer(string='Employees', compute='_compute_counts')
    vehicle_count = fields.Integer(string='Vehicles', compute='_compute_counts')

    _sql_constraints = [
        ('unique_number_company', 'UNIQUE(contract_number, company_id)',
         'Contract number must be unique per company.'),
    ]

    def _compute_counts(self):
        for rec in self:
            rec.employee_count = self.env['field.pass.employee'].search_count([
                ('contract_id', '=', rec.id), ('active', '=', True),
            ])
            rec.vehicle_count = self.env['field.pass.vehicle'].search_count([
                ('contract_id', '=', rec.id), ('active', '=', True),
            ])

    def name_get(self):
        return [(r.id, f"{r.contract_number}{' — ' + r.description if r.description else ''}") for r in self]
