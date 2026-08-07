import uuid
from typing import Dict, Any, Tuple
from datetime import datetime
from urllib.parse import quote

class EmailExecutionProvider:
    """Abstract interface for sales outreach execution."""
    def validate_message(self, message: dict) -> Tuple[bool, str]:
        raise NotImplementedError

    def send_email(self, message: dict) -> dict:
        raise NotImplementedError


class SandboxEmailProvider(EmailExecutionProvider):
    """Sandbox implementation that mimics an email sending provider without sending real emails."""
    
    def validate_message(self, message: dict) -> Tuple[bool, str]:
        if not message:
            return False, "Message data is empty."
        
        email = message.get("email")
        if not email or str(email).lower() == "null":
            return False, "No valid email address found."
            
        if not message.get("subject"):
            return False, "Subject is missing."
            
        if not message.get("body"):
            return False, "Email body is missing."
            
        if message.get("status") == "NO_EMAIL":
            return False, "Message is marked as NO_EMAIL."
            
        return True, "Valid"

    def send_email(self, message: dict) -> dict:
        """Executes the sandbox email send."""
        sandbox_id = f"sandbox-email-{uuid.uuid4().hex[:8]}"
        
        # Return a structured execution result mimicking an API response
        return {
            "mode": "SANDBOX",
            "status": "SENT",
            "messageId": sandbox_id,
            "recipient": message.get("email"),
            "sentAt": datetime.utcnow().isoformat() + "Z"
        }


class BrowserGmailProvider(EmailExecutionProvider):
    """Builds Gmail compose links so the user can finish sending in Gmail."""

    def validate_message(self, message: dict) -> Tuple[bool, str]:
        if not message:
            return False, "Message data is empty."

        email = message.get("email")
        if not email or str(email).lower() == "null":
            return False, "No valid email address found."

        if not message.get("subject"):
            return False, "Subject is missing."

        if not message.get("body"):
            return False, "Email body is missing."

        if message.get("status") == "NO_EMAIL":
            return False, "Message is marked as NO_EMAIL."

        return True, "Valid"

    def send_email(self, message: dict) -> dict:
        """Returns a Gmail compose URL for the approved outreach draft."""
        recipient = (message.get("email") or "").strip()
        subject = (message.get("subject") or "").strip()
        body = (message.get("body") or "").strip()

        compose_url = (
            "https://mail.google.com/mail/?view=cm&fs=1&tf=1"
            f"&to={quote(recipient)}"
            f"&su={quote(subject)}"
            f"&body={quote(body)}"
        )

        return {
            "mode": "GMAIL_BROWSER",
            "status": "READY_TO_OPEN",
            "recipient": recipient,
            "subject": subject,
            "composeUrl": compose_url,
            "openedAt": datetime.utcnow().isoformat() + "Z",
        }

def get_email_provider(mode: str = "SANDBOX") -> EmailExecutionProvider:
    normalized_mode = (mode or "SANDBOX").upper()
    if normalized_mode == "SANDBOX":
        return SandboxEmailProvider()
    if normalized_mode in {"GMAIL_BROWSER", "GMAIL", "BROWSER_GMAIL", "GMAIL_WEB"}:
        return BrowserGmailProvider()
    raise ValueError(f"Unknown execution mode: {mode}")
