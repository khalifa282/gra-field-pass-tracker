# -*- coding: utf-8 -*-
from odoo.exceptions import UserError
from odoo import models, fields


class HrDepartment(models.Model):
    _inherit = 'hr.department'

    # ── Company link ──────────────────────────────────────────────────────────
    # Confirmed: doing the "future merge" now, ahead of the original plan —
    # needed so HR Request forms can cascade Company -> Department -> Contract.
    # Not required at the DB level (existing Departments predate this field
    # and won't have it set) — enforce "must pick one" only where it
    # actually matters (e.g. the new HR Request forms), not retroactively
    # here, to avoid breaking existing data on upgrade.
    fp_company_id = fields.Many2one(
        'field.pass.company', string='Company - الشركة',
        help='Which Company (Administration → Companies) this department belongs to.',
    )

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

    # ── OPS role assignment — confirmed design: replaces Focal Points
    # entirely. Each slot is a res.users Many2one, domain-filtered to only
    # show users who actually hold the matching OPS group. This single set
    # of fields serves TWO purposes at once: (1) who has OPS-tier access to
    # this department (feeds the department-walling record rule), and (2)
    # who receives notifications for this department's events — replacing
    # Focal Points for that purpose too. One Manager slot, two Admin slots
    # (1+1 optional), three Viewer slots (1+2 optional) — none are
    # database-required, since departments may not have every role filled
    # in immediately. ────────────────────────────────────────────────────────
    ops_manager_id = fields.Many2one(
        'res.users', string='Manager - المدير',
        domain="[('groups_id.name', '=', 'OPS Manager')]",
    )
    ops_admin1_id = fields.Many2one(
        'res.users', string='Admin 1 - المسؤول 1',
        domain="[('groups_id.name', '=', 'OPS Admin')]",
    )
    ops_admin2_id = fields.Many2one(
        'res.users', string='Admin 2 (Optional) - المسؤول 2 (اختياري)',
        domain="[('groups_id.name', '=', 'OPS Admin')]",
    )
    ops_viewer1_id = fields.Many2one(
        'res.users', string='Viewer 1 - المشاهد 1',
        domain="[('groups_id.name', '=', 'OPS Viewer')]",
    )
    ops_viewer2_id = fields.Many2one(
        'res.users', string='Viewer 2 (Optional) - المشاهد 2 (اختياري)',
        domain="[('groups_id.name', '=', 'OPS Viewer')]",
    )
    ops_viewer3_id = fields.Many2one(
        'res.users', string='Viewer 3 (Optional) - المشاهد 3 (اختياري)',
        domain="[('groups_id.name', '=', 'OPS Viewer')]",
    )

    def _get_ops_user_ids(self):
        """All 6 slots, whichever are actually filled in — used by both the
        department-walling record rule and notification recipient lookup."""
        self.ensure_one()
        users = self.ops_manager_id | self.ops_admin1_id | self.ops_admin2_id \
            | self.ops_viewer1_id | self.ops_viewer2_id | self.ops_viewer3_id
        return users

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
