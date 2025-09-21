# agents/email_monitor.py - EMAIL-DRIVEN CONTRACT INGESTION
from __future__ import annotations
import asyncio
import email
import imaplib
import smtplib
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from email.mime.text import MimeText
from email.mime.multipart import MimeMultipart
from email.mime.base import MimeBase
from email import encoders
import io
import re
from datetime import datetime, timedelta
from loguru import logger

from .orchestrator import ContractOrchestrator
from api.settings import settings

@dataclass
class EmailContract:
    """Contract received via email"""
    message_id: str
    sender_email: str
    subject: str
    received_date: datetime
    attachment_filename: str
    attachment_bytes: bytes
    body_text: str

class EmailContractMonitor:
    """Monitor email for incoming contracts and process them automatically"""
    
    def __init__(self, orchestrator: ContractOrchestrator):
        self.orchestrator = orchestrator
        self.processed_messages: set = set()
        self.contract_patterns = [
            r'\b(contract|agreement|nda|terms)\b',
            r'\b(review|sign|signature)\b',
            r'\b(legal|attorney|counsel)\b'
        ]
        
    async def monitor_email_folder(
        self, 
        imap_server: str,
        email_addr: str, 
        password: str,
        folder: str = "INBOX",
        check_interval: int = 300  # 5 minutes
    ):
        """Continuously monitor email folder for contracts"""
        logger.info(f"📧 Starting email monitor for {email_addr}")
        
        while True:
            try:
                contracts = await self._check_for_contracts(
                    imap_server, email_addr, password, folder
                )
                
                for contract in contracts:
                    if contract.message_id not in self.processed_messages:
                        await self._process_email_contract(contract)
                        self.processed_messages.add(contract.message_id)
                
                logger.info(f"📬 Checked email: {len(contracts)} new contracts found")
                await asyncio.sleep(check_interval)
                
            except Exception as e:
                logger.error(f"Email monitoring error: {e}")
                await asyncio.sleep(60)  # Wait 1 minute on error
    
    async def _check_for_contracts(
        self,
        imap_server: str,
        email_addr: str, 
        password: str,
        folder: str
    ) -> List[EmailContract]:
        """Check email folder for potential contracts"""
        contracts = []
        
        try:
            # Connect to IMAP server
            mail = imaplib.IMAP4_SSL(imap_server)
            mail.login(email_addr, password)
            mail.select(folder)
            
            # Search for recent emails with attachments
            since_date = (datetime.now() - timedelta(hours=24)).strftime("%d-%b-%Y")
            status, messages = mail.search(None, f'(SINCE "{since_date}")')
            
            if status == "OK":
                message_ids = messages[0].split()
                
                for msg_id in message_ids[-50:]:  # Last 50 messages
                    try:
                        contract = await self._extract_contract_from_message(mail, msg_id)
                        if contract:
                            contracts.append(contract)
                    except Exception as e:
                        logger.warning(f"Failed to process message {msg_id}: {e}")
            
            mail.close()
            mail.logout()
            
        except Exception as e:
            logger.error(f"IMAP connection failed: {e}")
        
        return contracts
    
    async def _extract_contract_from_message(
        self, 
        mail: imaplib.IMAP4_SSL, 
        msg_id: bytes
    ) -> Optional[EmailContract]:
        """Extract contract from email message if present"""
        try:
            status, msg_data = mail.fetch(msg_id, "(RFC822)")
            if status != "OK":
                return None
                
            email_body = msg_data[0][1]
            email_message = email.message_from_bytes(email_body)
            
            # Extract basic info
            sender = email_message["From"]
            subject = email_message["Subject"] or ""
            date_str = email_message["Date"] or ""
            message_id = email_message["Message-ID"] or str(msg_id)
            
            # Check if this looks like a contract-related email
            combined_text = f"{subject} {self._get_email_body(email_message)}"
            if not self._looks_like_contract_email(combined_text):
                return None
            
            # Look for contract attachments
            for part in email_message.walk():
                if part.get_content_disposition() == "attachment":
                    filename = part.get_filename()
                    if filename and self._is_contract_file(filename):
                        attachment_bytes = part.get_payload(decode=True)
                        
                        return EmailContract(
                            message_id=message_id,
                            sender_email=sender,
                            subject=subject,
                            received_date=self._parse_email_date(date_str),
                            attachment_filename=filename,
                            attachment_bytes=attachment_bytes,
                            body_text=combined_text[:500]  # First 500 chars
                        )
            
        except Exception as e:
            logger.warning(f"Message extraction failed: {e}")
        
        return None
    
    def _get_email_body(self, email_message) -> str:
        """Extract text body from email message"""
        body = ""
        try:
            if email_message.is_multipart():
                for part in email_message.walk():
                    if part.get_content_type() == "text/plain":
                        body += part.get_payload(decode=True).decode("utf-8", errors="ignore")
            else:
                body = email_message.get_payload(decode=True).decode("utf-8", errors="ignore")
        except Exception:
            body = ""
        return body
    
    def _looks_like_contract_email(self, text: str) -> bool:
        """Check if email content suggests it contains a contract"""
        text_lower = text.lower()
        
        # Look for contract-related keywords
        matches = sum(1 for pattern in self.contract_patterns 
                     if re.search(pattern, text_lower))
        
        return matches >= 1
    
    def _is_contract_file(self, filename: str) -> bool:
        """Check if filename suggests a contract document"""
        filename_lower = filename.lower()
        
        # Check file extension
        contract_extensions = ['.pdf', '.docx', '.doc', '.txt']
        has_valid_extension = any(filename_lower.endswith(ext) for ext in contract_extensions)
        
        # Check filename keywords
        contract_keywords = ['contract', 'agreement', 'nda', 'terms', 'msa', 'sow']
        has_contract_keyword = any(keyword in filename_lower for keyword in contract_keywords)
        
        return has_valid_extension and (has_contract_keyword or filename_lower.startswith('contract'))
    
    def _parse_email_date(self, date_str: str) -> datetime:
        """Parse email date string to datetime"""
        try:
            from email.utils import parsedate_to_datetime
            return parsedate_to_datetime(date_str)
        except Exception:
            return datetime.now()
    
    async def _process_email_contract(self, contract: EmailContract):
        """Process a contract received via email"""
        logger.info(f"📧 Processing email contract: {contract.attachment_filename} from {contract.sender_email}")
        
        try:
            # Run the contract through the pipeline
            result = await self.orchestrator.process_contract(
                file_bytes=contract.attachment_bytes,
                filename=contract.attachment_filename,
                requester_email=contract.sender_email,
                strict_mode=False  # Be lenient with email attachments
            )
            
            # Send response email with analysis
            await self._send_analysis_response(contract, result)
            
            logger.info(f"✅ Processed email contract: {result.recommendation}")
            
        except Exception as e:
            logger.error(f"Failed to process email contract: {e}")
            await self._send_error_response(contract, str(e))
    
    async def _send_analysis_response(self, contract: EmailContract, result):
        """Send analysis results back to the sender"""
        try:
            from .tools_email import send_email_sendgrid
            
            # Create response subject
            response_subject = f"Contract Analysis Complete: {result.recommendation}"
            
            # Create HTML response
            html_content = f"""
<h2>Contract Analysis Results</h2>
<p>Dear {contract.sender_email.split('@')[0]},</p>

<p>We've completed the automated analysis of your contract: <b>{contract.attachment_filename}</b></p>

<div style="padding: 15px; background-color: {'red' if result.recommendation == 'REJECT' else 'orange' if result.recommendation == 'NEGOTIATE' else 'green'}; color: white;">
    <h3>RECOMMENDATION: {result.recommendation}</h3>
    <p>Risk Score: {result.risk_score}/100</p>
</div>

<h3>Key Findings:</h3>
<ul>
    <li><b>Contract Type:</b> {result.contract_type}</li>
    <li><b>Critical Issues:</b> {len(result.critical_issues)}</li>
    <li><b>Processing Time:</b> {result.processing_time_seconds:.2f} seconds</li>
</ul>

<h3>Next Steps:</h3>
<ol>
{''.join(f'<li>{step}</li>' for step in result.next_steps)}
</ol>

<p>For detailed analysis, please use our web interface or contact our legal team.</p>

<p><i>This is an automated response from Pactify Contract Analyzer.</i></p>
"""
            
            # Send response
            send_email_sendgrid(
                to_email=contract.sender_email,
                subject=response_subject,
                body=html_content
            )
            
        except Exception as e:
            logger.error(f"Failed to send analysis response: {e}")
    
    async def _send_error_response(self, contract: EmailContract, error: str):
        """Send error response if processing fails"""
        try:
            from .tools_email import send_email_sendgrid
            
            html_content = f"""
<h2>Contract Analysis Failed</h2>
<p>Dear {contract.sender_email.split('@')[0]},</p>

<p>We encountered an issue processing your contract: <b>{contract.attachment_filename}</b></p>

<p><b>Error:</b> {error}</p>

<p>Please ensure:</p>
<ul>
    <li>File is a valid PDF, DOCX, or TXT document</li>
    <li>Document contains readable contract text</li>
    <li>File size is under 10MB</li>
</ul>

<p>You can also try uploading via our web interface at [your-domain]/analyze</p>

<p><i>Pactify Contract Analyzer</i></p>
"""
            
            send_email_sendgrid(
                to_email=contract.sender_email,
                subject="Contract Analysis Failed",
                body=html_content
            )
            
        except Exception as e:
            logger.error(f"Failed to send error response: {e}")
    
    def get_monitoring_stats(self) -> Dict[str, Any]:
        """Get email monitoring statistics"""
        return {
            "processed_messages": len(self.processed_messages),
            "monitoring_status": "active",
            "contract_patterns": len(self.contract_patterns)
        }

# Example usage function
async def start_email_monitoring():
    """Example function to start email monitoring"""
    orchestrator = ContractOrchestrator()
    monitor = EmailContractMonitor(orchestrator)
    
    # Example configuration - replace with your email settings
    await monitor.monitor_email_folder(
        imap_server="imap.gmail.com",  # or your email provider
        email_addr="contracts@yourcompany.com",
        password="your-app-password",  # use app-specific password
        folder="INBOX",
        check_interval=300  # Check every 5 minutes
    )
