# agents/tools_email.py
from __future__ import annotations
from typing import Optional, Dict, Any
import base64

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content, Attachment, FileContent, FileName, FileType, Disposition
from api.settings import settings


def _clean(s: Optional[str]) -> Optional[str]:
    return s.strip() if isinstance(s, str) else s


def send_email_sendgrid(
    to_email: str,
    subject: str,
    body: str,
    attachment_bytes: bytes | None = None,
    attachment_name: str | None = None,
    attachment_mime: str | None = None,
) -> Dict[str, Any]:
    """
    Sends an email via SendGrid using SENDGRID_API_KEY and EMAIL_SENDER from settings.
    We defensively strip whitespace from secrets to avoid 'Invalid header value' (trailing newline).
    """
    api_key = _clean(settings.sendgrid_api_key)
    sender = _clean(settings.email_sender)

    if not api_key:
        raise RuntimeError("SENDGRID_API_KEY not set")
    if not sender:
        raise RuntimeError("EMAIL_SENDER not set (and must be a verified Single Sender / domain)")

    message = Mail(
        from_email=Email(sender),
        to_emails=[To(_clean(to_email))],
        subject=_clean(subject) or "Message",
        html_content=Content("text/html", body or "<p>(no body)</p>"),
    )

    if attachment_bytes:
        encoded = base64.b64encode(attachment_bytes).decode("utf-8")
        att = Attachment()
        att.file_content = FileContent(encoded)
        att.file_name = FileName(attachment_name or "attachment.bin")
        att.file_type = FileType(attachment_mime or "application/octet-stream")
        att.disposition = Disposition("attachment")
        message.attachment = att

    sg = SendGridAPIClient(api_key)
    resp = sg.send(message)
    return {"status_code": resp.status_code}
