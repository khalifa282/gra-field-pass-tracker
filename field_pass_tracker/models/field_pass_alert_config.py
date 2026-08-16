# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class FieldPassAlertConfig(models.Model):
    _name = 'field.pass.alert.config'
    _description = 'Field Pass Alert Configuration'
    _order = 'document_type asc'

    company_id = fields.Many2one(
        'res.company', string='Company', required=True,
        default=lambda self: self.env.company, ondelete='cascade',
    )
    document_type = fields.Selection(
        selection=[
            ('passport', 'Passport'),
            ('residency', 'Residency'),
            ('civil_id', 'Civil ID'),
            ('driving_license', 'Driving License'),
            ('driving_authority', 'Driving Authority'),
            ('driving_hse', 'Driving HSE Training'),
            ('ptw', 'PTW'),
            ('koc_laptop', 'KOC Laptop Pass'),
            ('registration', 'Registration'),
            ('third_party_inspection', '3rd Party Inspection'),
            ('third_party_inspection_duration', '3rd Party Inspection Duration (days)'),
            ('clearance_certificate', 'Clearance Certificate'),
            ('fp_koc', 'KOC Field Pass'),
            ('fp_ratqa_abdally', 'RATQA & Abdally GP'),
            ('fp_wafra', 'Wafra Field Pass'),
            ('fp_fawares', 'Fawares Field Pass'),
            ('fp_temp', 'Temp Field Pass'),
            ('company_doc', 'Company Document (single threshold, all types)'),
        ],
        string='Document Type', required=True,
    )
    warn_days_before = fields.Integer(string='Warning Days (internal)', required=True, default=30)
    warn_months = fields.Integer(string='Warning Period (Months)', compute='_compute_warn_months', inverse='_inverse_warn_months', store=False)

    @api.depends('warn_days_before')
    def _compute_warn_months(self):
        for rec in self:
            rec.warn_months = round(rec.warn_days_before / 30)

    def _inverse_warn_months(self):
        for rec in self:
            rec.warn_days_before = max(1, rec.warn_months * 30)

    _sql_constraints = [
        ('unique_company_doc', 'UNIQUE(company_id, document_type)',
         'Each document type can only have one configuration per company.'),
    ]

    @api.constrains('warn_days_before')
    def _check_days(self):
        for rec in self:
            if rec.warn_days_before < 1:
                raise ValidationError('Warning days must be at least 1.')

    @api.model
    def get_warn_days(self, document_type, company_id=None):
        if not company_id:
            company_id = self.env.company.id
        config = self.search([
            ('company_id', '=', company_id),
            ('document_type', '=', document_type),
        ], limit=1)
        return config.warn_days_before if config else 30

    @api.model
    def get_inspection_duration(self, company_id=None):
        if not company_id:
            company_id = self.env.company.id
        config = self.search([
            ('company_id', '=', company_id),
            ('document_type', '=', 'third_party_inspection_duration'),
        ], limit=1)
        return config.warn_days_before if config else 365
