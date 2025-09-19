import os, base64
import requests
from loguru import logger
from docusign_esign import ApiClient, EnvelopesApi, EnvelopeDefinition, Document, Signer, SignHere, Tabs, Recipients

BASE_URL = os.environ.get("DOCUSIGN_BASE_URL")
INTEGRATOR_KEY = os.environ.get("DOCUSIGN_INTEGRATOR_KEY")
USER_ID = os.environ.get("DOCUSIGN_USER_ID")
PRIVATE_KEY_PATH = os.environ.get("DOCUSIGN_PRIVATE_KEY_PATH")

# For MVP demo, stub a simple "send document" call

def send_contract_for_signature(file_bytes: bytes, filename: str, signer_email: str, signer_name: str):
    """
    Very simplified DocuSign send for signature (demo stub).
    In production, use the official docusign-esign SDK with JWT.
    """
    try:
        # This is where you'd normally create an envelope via API.
        # For demo, just log and pretend.
        logger.info(f"[DocuSign Stub] Sending {filename} to {signer_name} <{signer_email}>")
        return {
            "status": "sent",
            "signer": signer_email,
            "envelopeId": "demo-envelope-123"
        }
    except Exception as e:
        logger.error(e)
        return {"status": "error", "error": str(e)}
    
def send_contract_for_signature(file_bytes: bytes, filename: str, signer_email: str, signer_name: str):
    base_path = os.environ.get("DOCUSIGN_BASE_URL", "https://demo.docusign.net/restapi")
    integrator_key = os.environ.get("DOCUSIGN_INTEGRATOR_KEY")
    user_id = os.environ.get("DOCUSIGN_USER_ID")
    private_key_path = os.environ.get("DOCUSIGN_PRIVATE_KEY_PATH")

    api_client = ApiClient()
    api_client.host = base_path

    # Auth via JWT (DocuSign demo uses 10 min tokens)
    api_client.configure_jwt_authorization_flow(
        private_key_path,
        "account-d.docusign.com",
        integrator_key,
        user_id,
        3600
    )

    # Build the envelope
    document = Document(
        document_base64=file_bytes.decode("latin1"),
        name=filename,
        file_extension=filename.split(".")[-1],
        document_id="1"
    )
    sign_here = SignHere(anchor_string="SIGN_HERE", anchor_units="pixels", anchor_x_offset="100", anchor_y_offset="100")
    signer = Signer(email=signer_email, name=signer_name, recipient_id="1", routing_order="1", tabs=Tabs(sign_here_tabs=[sign_here]))
    recipients = Recipients(signers=[signer])
    envelope_definition = EnvelopeDefinition(email_subject="Please sign this contract", documents=[document], recipients=recipients, status="sent")

    # Send envelope
    envelopes_api = EnvelopesApi(api_client)
    results = envelopes_api.create_envelope("me", envelope_definition=envelope_definition)
    return {"status": "sent", "signer": signer_email, "envelopeId": results.envelope_id}
