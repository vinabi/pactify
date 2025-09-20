# agents/tools_email.py
from __future__ import annotations
import base64
import os
from typing import Optional

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content, Attachment, FileContent, FileName, FileType, Disposition

def _env_trim(name: str) -> str:
    v = os.getenv(name, "")
    return v.strip() if v else ""

def send_email_sendgrid(
    to_email: str,
    subject: str,
    body: str,
    attachment_bytes: Optional[bytes] = None,
    attachment_name: Optional[str] = None,
    attachment_mime: Optional[str] = None,
):
    api_key = _env_trim("SENDGRID_API_KEY")
    sender = _env_trim("EMAIL_SENDER")

    if not api_key or not api_key.startswith("SG."):
        raise RuntimeError("SENDGRID_API_KEY missing/invalid (must start with 'SG.').")
    if not sender or "@" not in sender:
        raise RuntimeError("EMAIL_SENDER missing/invalid or not verified in SendGrid.")

    message = Mail(
        from_email=Email(sender),
        to_emails=To(to_email),
        subject=subject,
        plain_text_content=Content("text/plain", body or ""),
    )

    if attachment_bytes and attachment_name:
        b64 = base64.b64encode(attachment_bytes).decode("ascii")
        att = Attachment(
            FileContent(b64),
            FileName(attachment_name),
            FileType(attachment_mime or "application/octet-stream"),
            Disposition("attachment"),
        )
        message.attachment = att

    sg = SendGridAPIClient(api_key)
    resp = sg.send(message)
    return {"status_code": resp.status_code}
