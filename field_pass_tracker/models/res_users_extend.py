# -*- coding: utf-8 -*-
from odoo import models, fields


class ResUsers(models.Model):
    _inherit = 'res.users'

    # Confirmed design: OPS Viewer/Admin/Manager are fully walled off outside
    # these department(s) — enforced via a record rule reading this field
    # (see field_pass_security.xml's OPS record rule). Not used at all by
    # GRO/HR tiers, who remain company-wide regardless of what's set here.
    fp_ops_department_ids = fields.Many2many(
        'hr.department', 'fp_user_ops_department_rel', 'user_id', 'department_id',
        string='OPS Departments - أقسام العمليات',
        help='Which department(s) this user can see/act on when using OPS-tier '
             'access. Irrelevant for GRO/HR-tier access, which stays company-wide.',
    )
