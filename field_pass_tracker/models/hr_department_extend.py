# -*- coding: utf-8 -*-
from odoo.exceptions import UserError
from odoo import models, fields


class HrDepartment(models.Model):
    _inherit = 'hr.department'

    # ── Clients ───────────────────────────────────────────────────────────────
    fp_client_koc = fields.Boolean(
        string='Kuwait Oil Company (KOC)',
        default=False,
        help='Requires: KOC Field Pass, RATQA & Abdally Pass, CV Approval.',
    )
    fp_client_wjo = fields.Boolean(
        string='Wafra Joint Operations (WJO)',
        default=False,
        help='Requires: Wafra Pass, Fawares Pass, WJO HSE Training.',
    )
    def unlink(self):
        for dept in self:
            emp_count = self.env['field.pass.employee'].search_count(
                [('department_id', '=', dept.id)])
            veh_count = self.env['field.pass.vehicle'].search_count(
                [('department_id', '=', dept.id)])
            if emp_count or veh_count:
                raise UserError(
                    f'Cannot delete "{dept.name}" — it has {emp_count} employee(s) and '
                    f'{veh_count} vehicle(s) linked to it.\n'
                    f'Please archive it instead: Action > Archive.'
                )
        return super().unlink()
