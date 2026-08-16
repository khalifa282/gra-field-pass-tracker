# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError

# Company documents share ONE global reminder threshold (confirmed design —
# unlike Employee/Vehicle documents, which each have their own threshold).
# Configured via the SAME Alert Settings screen as everything else
# (document_type = 'company_doc' in field.pass.alert.config), not a hidden
# system parameter — so it's actually discoverable/editable in the UI.

# Prerequisite links live in this many2many relation table — declared here
# explicitly (both directions reference the SAME model) so the reverse
# field below can share it.
PREREQ_REL_TABLE = 'field_pass_company_doc_prereq_rel'


class FieldPassCompanyDocument(models.Model):
    _name = 'field.pass.company.document'
    _description = 'Company Document (user-defined type, with configurable prerequisites)'
    _order = 'level, name'

    name = fields.Char(required=True)
    name_ar = fields.Char(string='Arabic Name - الاسم بالعربية')
    related_authority = fields.Char(
        string='Related Ministry/Government Body - الجهة الحكومية المعنية',
        help='Free text — e.g. "Ministry of Commerce", "Kuwait Municipality".',
    )
    company_id = fields.Many2one(
        'field.pass.company', required=True, ondelete='cascade', index=True,
        default=lambda self: self.env.context.get('default_company_id'),
        help='Auto-filled from context wherever possible — a FIELD-level default '
             '(not just relying on the action context dict), so it also correctly '
             'fills in for nested creation dialogs (e.g. from within a Prerequisites '
             'picker), not just the top-level "New" button.',
    )
    active = fields.Boolean(default=True)

    # Prerequisites — deliberately unrestricted in COUNT (can require any
    # number of other documents, confirmed design: "needs 4 documents").
    # Domain restricts choices to the SAME company only (confirmed:
    # prerequisites never span companies).
    prerequisite_ids = fields.Many2many(
        'field.pass.company.document', PREREQ_REL_TABLE,
        'document_id', 'prerequisite_id',
        string='Prerequisites - المتطلبات المسبقة',
        domain="[('company_id', '=', company_id), ('id', '!=', id)]",
        help='"Add a line" only lets you pick documents that already exist in this same '
             'company — create the prerequisite as its own document first, then come back '
             'and link it here. Click an existing row below to open THAT document\'s own '
             'page (where you\'ll see its prerequisites the same way, nested as many '
             'levels deep as needed).\n'
             '"إضافة سطر" يتيح فقط اختيار مستندات موجودة بالفعل في نفس الشركة — أنشئ '
             'المستند المطلوب أولاً، ثم عد واربطه هنا. انقر على أي صف موجود أدناه لفتح '
             'صفحة ذلك المستند.',
    )
    # Reverse relation — "what depends on me" — read-only, purely for
    # convenience when reviewing a document (e.g. "3 other documents rely
    # on this one being kept current").
    dependent_ids = fields.Many2many(
        'field.pass.company.document', PREREQ_REL_TABLE,
        'prerequisite_id', 'document_id',
        string='Required By - مطلوب من قبل',
    )

    validity_date = fields.Date(string='Expiry Date - تاريخ الانتهاء')
    attachment = fields.Binary(string='Document Copy - نسخة المستند', attachment=True)
    attachment_name = fields.Char()

    status = fields.Selection([
        ('valid', 'Valid'), ('warning', 'Warning'),
        ('expired', 'Expired'), ('na', 'Not Set'),
    ], compute='_compute_status', store=True)
    days_remaining = fields.Integer(compute='_compute_status', store=True)

    # A document is "main" when nothing else requires it — confirmed rule.
    # This is what "Manage Documents" filters on, so the top-level list
    # only shows entry points (like Commercial License), never sub-
    # documents (like Registration) cluttering the same list.
    is_main = fields.Boolean(compute='_compute_is_main', store=True)

    @api.depends('dependent_ids')
    def _compute_is_main(self):
        for r in self:
            r.is_main = not bool(r.dependent_ids)

    # 0 = no prerequisites (root). Otherwise 1 + the deepest prerequisite's
    # level. Purely for display/sorting (matches the "0-A / 1-A" naming
    # from the original spec) — NOT used for any validation logic itself;
    # _check_prerequisites_valid below checks actual prerequisite STATUS,
    # not level, so level being cosmetic can't cause a validation gap.
    level = fields.Integer(compute='_compute_level', store=True)

    # ── Level (safe, bounded traversal — see module docstring note) ─────────
    @api.depends('prerequisite_ids.level')
    def _compute_level(self):
        for r in self:
            r.level = r._get_level_safe(set())

    def _get_level_safe(self, visited):
        """
        Defensively bounded — if a cycle somehow exists in memory (e.g. the
        brief moment before _check_no_cycles below blocks the save), this
        returns a safe fallback (0) instead of recursing forever and
        crashing with a RecursionError. The constrains check is what
        actually PREVENTS cycles from being saved in the first place; this
        is just a safety net so level computation itself can never crash.
        """
        self.ensure_one()
        if self.id in visited or not self.prerequisite_ids:
            return 0
        visited = visited | {self.id}
        return 1 + max(
            (p._get_level_safe(visited) for p in self.prerequisite_ids),
            default=0,
        )

    # ── Status (uses the single "Company Document" threshold, configured
    # via the same Alert Settings screen as everything else — Administration
    # → Alert Settings — not a hidden system parameter.) ────────────────────
    #
    # Confirmed design: a document's overall status also reflects its
    # prerequisites — if "Registration" is in warning, "Commercial License"
    # (which requires it) shows warning too, even if its OWN expiry date is
    # fine. This propagates through the whole chain automatically: each
    # prerequisite's `status` is ALREADY its own fully-combined value (via
    # this exact same computation, recursively), so taking the worst of
    # "this document's own date-based status" + "its DIRECT prerequisites'
    # already-computed status" correctly carries multi-level chains upward
    # without needing custom recursive traversal — Odoo's own dependency
    # graph handles the propagation, the same way it already does for
    # `level` above.
    _STATUS_RANK = {'expired': 2, 'warning': 1, 'valid': 0, 'na': -1}

    @api.depends('validity_date', 'prerequisite_ids.status')
    def _compute_status(self):
        warn_days = self.env['field.pass.alert.config'].get_warn_days('company_doc')
        today = fields.Date.today()
        for r in self:
            if not r.validity_date:
                own_status, r.days_remaining = 'na', 0
            else:
                delta = (r.validity_date - today).days
                r.days_remaining = delta
                if delta < 0:
                    own_status = 'expired'
                elif delta <= warn_days:
                    own_status = 'warning'
                else:
                    own_status = 'valid'

            candidates = [own_status] + r.prerequisite_ids.mapped('status')
            r.status = max(candidates, key=lambda s: r._STATUS_RANK.get(s, -1))

    # ── Hard guards: no self-reference, no cycles of any length ──────────────
    @api.constrains('prerequisite_ids')
    def _check_no_self_reference(self):
        for r in self:
            if r in r.prerequisite_ids:
                raise ValidationError(
                    f'"{r.name}" cannot be listed as its own prerequisite.'
                )

    @api.constrains('prerequisite_ids')
    def _check_no_cycles(self):
        for r in self:
            visited = set()

            def visit(doc):
                if doc.id in visited:
                    raise ValidationError(
                        f'Circular prerequisite detected involving "{doc.name}". '
                        f'A document cannot require itself, even indirectly '
                        f'through a chain of other documents.'
                    )
                visited.add(doc.id)
                for prereq in doc.prerequisite_ids:
                    visit(prereq)

            visit(r)

    # ── Prerequisite enforcement — mirrors the Employee/Vehicle domino
    # pattern used everywhere else in this module: can't set an expiry
    # date until every prerequisite is itself currently valid/warning. ────
    @api.constrains('validity_date', 'prerequisite_ids')
    def _check_prerequisites_valid(self):
        OK = ('valid', 'warning')
        for r in self:
            if not r.validity_date:
                continue
            not_ready = r.prerequisite_ids.filtered(lambda p: p.status not in OK)
            if not_ready:
                names = ', '.join(not_ready.mapped('name'))
                raise ValidationError(
                    f'Cannot set an expiry date for "{r.name}": '
                    f'the following prerequisites must be valid first: {names}.'
                )
