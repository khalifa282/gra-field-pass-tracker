# -*- coding: utf-8 -*-
from odoo import models, fields, api


class FieldPassCompany(models.Model):
    _name = 'field.pass.company'
    _description = 'Company (standalone corporate entity — not yet linked to res.company)'
    _order = 'name'

    name = fields.Char(string='English Name - الاسم بالإنجليزية', required=True)
    name_ar = fields.Char(string='Arabic Name - الاسم بالعربية')
    acronym = fields.Char(string='Acronym - الاختصار')
    phone = fields.Char(string='Phone - الهاتف')
    fax = fields.Char(string='Fax - الفاكس')
    email = fields.Char(string='Email - البريد الإلكتروني')
    active = fields.Boolean(default=True)
    remarks = fields.Text()

    document_ids = fields.One2many('field.pass.company.document', 'company_id', string='Documents')
    document_count = fields.Integer(
        compute='_compute_document_count',
        help='Count of MAIN documents only (matches what "Manage Documents" shows) — '
             'sub-documents are not counted here separately, to avoid a confusing '
             'mismatch between this number and what you see after clicking in.',
    )

    overall_status = fields.Selection([
        ('valid', 'Valid'), ('warning', 'Warning'),
        ('expired', 'Expired'), ('na', 'No Documents'),
    ], compute='_compute_overall_status', store=True)

    def _compute_document_count(self):
        for r in self:
            r.document_count = len(r.document_ids.filtered('is_main'))

    @api.depends('document_ids.status')
    def _compute_overall_status(self):
        RANK = {'expired': 2, 'warning': 1, 'valid': 0, 'na': -1}
        for r in self:
            statuses = r.document_ids.filtered(lambda d: d.active).mapped('status')
            if not statuses:
                r.overall_status = 'na'
            else:
                r.overall_status = max(statuses, key=lambda s: RANK.get(s, -1))

    def action_view_documents(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Documents — {self.name}',
            'res_model': 'field.pass.company.document',
            'view_mode': 'tree,form',
            'domain': [('company_id', '=', self.id), ('is_main', '=', True)],
            'context': {'default_company_id': self.id},
        }

    def action_duplicate_documents_from(self, source_company_id):
        """
        Copies another company's document CHECKLIST (names + prerequisite
        structure) into this company as a starting point — deliberately
        does NOT copy validity dates or attachments, since those are
        specific to the source company's actual paperwork, not something
        that should carry over to a different company.
        """
        self.ensure_one()
        source = self.env['field.pass.company'].browse(source_company_id)
        if not source or source.id == self.id:
            return
        # Two passes: first create all documents (no prerequisites yet, since
        # prerequisites reference OTHER new documents that don't exist until
        # created), then wire up the prerequisite links using the mapping
        # from old document id -> newly created document id.
        old_to_new = {}
        for doc in source.document_ids.filtered(lambda d: d.active):
            new_doc = self.env['field.pass.company.document'].create({
                'name': doc.name,
                'name_ar': doc.name_ar,
                'related_authority': doc.related_authority,
                'company_id': self.id,
            })
            old_to_new[doc.id] = new_doc.id
        for doc in source.document_ids.filtered(lambda d: d.active):
            if doc.prerequisite_ids:
                new_doc = self.env['field.pass.company.document'].browse(old_to_new[doc.id])
                new_doc.prerequisite_ids = [(6, 0, [
                    old_to_new[p.id] for p in doc.prerequisite_ids if p.id in old_to_new
                ])]
