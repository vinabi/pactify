# agents/tools_email.py
from __future__ import annotations
import base64
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Attachment, FileContent, FileName, FileType, Disposition
from api.settings import settings

def send_email_sendgrid(
    to_email: str,
    subject: str,
    body: str,
    attachment_bytes: bytes | None = None,
    attachment_name: str | None = None,
    attachment_mime: str = "application/octet-stream",
):
    api_key = (settings.sendgrid_api_key or "").strip().strip('"').strip("'")
    sender  = (settings.email_sender or "").strip().strip('"').strip("'")
    if not api_key:
        raise RuntimeError("SENDGRID_API_KEY not set")
    if not sender or "@" not in sender:
        raise RuntimeError("EMAIL_SENDER not set/verified")

    msg = Mail(from_email=sender, to_emails=to_email, subject=subject, html_content=body)

    if attachment_bytes:
        enc = base64.b64encode(attachment_bytes).decode()
        att = Attachment(
            file_content=FileContent(enc),
            file_type=FileType(attachment_mime),
            file_name=FileName(attachment_name or "contract.txt"),
            disposition=Disposition("attachment"),
        )
        msg.attachment = att

    sg = SendGridAPIClient(api_key)  # pass raw key; do NOT prepend "Bearer "
    resp = sg.send(msg)
    return {"status_code": resp.status_code}
