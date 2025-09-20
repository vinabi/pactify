# agents/tools_email.py
from __future__ import annotations
import base64, os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Attachment, ContentId, Disposition, FileName, FileContent, FileType
from api.settings import settings

def send_email_sendgrid(to_email: str, subject: str, body: str,
                        attachment_bytes: bytes | None = None,
                        attachment_name: str | None = None):
    api_key = (settings.sendgrid_api_key or os.getenv("SENDGRID_API_KEY") or "").strip().strip('"').strip()
    sender = (settings.email_sender or os.getenv("EMAIL_SENDER") or "").strip()
    if not api_key:
        raise RuntimeError("SENDGRID_API_KEY not set")
    if not sender:
        raise RuntimeError("EMAIL_SENDER not set or not verified in SendGrid")

    message = Mail(from_email=sender, to_emails=to_email, subject=subject, html_content=body)

    if attachment_bytes and attachment_name:
        enc = base64.b64encode(attachment_bytes).decode("ascii")
        att = Attachment()
        att.file_content = FileContent(enc)
        att.file_type = FileType("application/octet-stream")
        att.file_name = FileName(attachment_name)
        att.disposition = Disposition("attachment")
        att.content_id = ContentId("Contract")
        message.attachment = att

    sg = SendGridAPIClient(api_key)  # pass clean key; library will set Authorization header
    resp = sg.send(message)
    return {"status_code": resp.status_code}
