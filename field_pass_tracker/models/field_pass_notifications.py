# -*- coding: utf-8 -*-
"""
Shared helper for sending Field Pass notifications — used by Submit/Reject/
Issue actions (Stage 3) and the expiry-warning cron (Stage 4). Plain
function, not a model, so it can be called from any of the wizard/model
files without import-order complications.
"""

STATUS_WORDS = {
    'submitted': 'Submitted',
    'rejected': 'Rejected',
    'issued': 'Issued',
    'warning': 'Near Expiry',
    'expired': 'Expired',
}


def notify_track(env, group_xml_id, subject, body_html):
    """
    Plain notification to every user holding the given group (Viewer-tier
    and up — Admin/Manager auto-inherit membership via implied_ids, so
    checking the base Viewer-tier group alone covers all 3 tiers of that
    track). Used for anything that isn't department-scoped: Company
    Document alerts (GRO-wide) and HR Request notifications (GRO<->HR,
    company-wide on both sides).
    """
    group = env.ref(group_xml_id)
    recipients = [u.email for u in group.users if u.email]
    if not recipients:
        return
    env['mail.mail'].sudo().create({
        'subject': subject,
        'body_html': body_html,
        'email_to': ','.join(recipients),
    }).send()


def send_fp_notification(env, entity, document_label, alert_type,
                          event_by_name='', extra_note='',
                          document_type_key='', expiry_date=None):
    """
    entity: a single Employee or Vehicle record (field.pass.employee /
        field.pass.vehicle) — whichever this alert is about.
    document_label: human-readable label, e.g. 'Passport', 'KOC Field Pass'.
    alert_type: 'submitted' / 'rejected' / 'issued' / 'warning' / 'expired'.
    event_by_name: who triggered it (blank for system-generated
        warning/expired alerts).
    extra_note: optional extra line — rejection reason, new expiry date, etc.
    document_type_key / expiry_date: only used by the Stage 4 cron, to log
        enough detail for the dedup check (already_sent()) to work
        correctly across renewal cycles. Submitted/Rejected/Issued callers
        can leave these blank — see field_pass_alert_log.py's docstring on
        already_sent() for why those don't need dedup at all.

    Silently does nothing if the entity's department has no OPS user
    assigned with a usable email set — confirmed behavior, not a bug: some
    departments may not have every OPS slot filled in yet.
    """
    dept = entity.department_id
    if not dept:
        return

    recipients = [u.email for u in dept.sudo()._get_ops_user_ids() if u.email]
    if not recipients:
        return

    entity_name = entity.name if hasattr(entity, 'name') else entity.plate_number
    status_word = STATUS_WORDS.get(alert_type, alert_type)
    subject = f'Field Pass Update — {document_label} {status_word}'

    body_lines = [
        f'<p><b>{document_label}</b> for <b>{entity_name}</b> ({dept.name})</p>',
        f'<p>Status: <b>{status_word}</b></p>',
    ]
    if event_by_name:
        body_lines.append(f'<p>By: {event_by_name}</p>')
    if extra_note:
        body_lines.append(f'<p>{extra_note}</p>')
    body_html = ''.join(body_lines)

    env['mail.mail'].sudo().create({
        'subject': subject,
        'body_html': body_html,
        'email_to': ','.join(recipients),
    }).send()

    env['field.pass.alert.log'].sudo().create({
        'res_model': entity._name,
        'res_id': entity.id,
        'entity_name': entity_name,
        'department_id': dept.id,
        'document_type': document_type_key or document_label,
        'document_expiry_date': expiry_date,
        'alert_type': alert_type,
        'recipient_emails': ','.join(recipients),
    })
