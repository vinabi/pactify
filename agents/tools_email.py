from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Attachment, FileContent, FileType, FileName, Disposition
from api.settings import settings
import base64

def send_email_sendgrid(
    to_email: str,
    subject: str,
    body: str,
    attachment_bytes: bytes | None = None,
    attachment_name: str | None = None,
):
    api_key = settings.sendgrid_api_key
    sender  = settings.email_sender
    if not api_key:
        raise RuntimeError("SENDGRID_API_KEY not set")
    if not sender:
        raise RuntimeError("EMAIL_SENDER not set or not verified in SendGrid")

    msg = Mail(from_email=sender, to_emails=to_email, subject=subject, html_content=body)

    if attachment_bytes and attachment_name:
        encoded = base64.b64encode(attachment_bytes).decode()
        att = Attachment(
            file_content=FileContent(encoded),
            file_type=FileType("application/octet-stream"),
            file_name=FileName(attachment_name),
            disposition=Disposition("attachment"),
        )
        msg.attachment = att

    resp = SendGridAPIClient(api_key).send(msg)
    return {"status_code": resp.status_code}
