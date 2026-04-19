from datetime import datetime, timezone

import requests

from src.services.formatter import EmailMessage


SENDGRID_URL = "https://api.sendgrid.com/v3/mail/send"


class SendGridEmailSender:
    """Sends one prepared email through SendGrid."""

    def __init__(self, api_key: str, sender: str, recipient: str) -> None:
        self.api_key = api_key
        self.sender = sender
        self.recipient = recipient

    def send(self, message: EmailMessage) -> dict:
        payload = self._build_payload(message)
        headers = self._build_headers()

        response = requests.post(SENDGRID_URL, json=payload, headers=headers, timeout=20)
        response.raise_for_status()

        return self._build_send_result(message, response)

    def _build_payload(self, message: EmailMessage) -> dict:
        return {
            "personalizations": [{"to": [{"email": self.recipient}]}],
            "from": {"email": self.sender},
            "subject": message.subject,
            "content": [{"type": "text/html", "value": message.html}],
        }

    def _build_headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _build_send_result(self, message: EmailMessage, response: requests.Response) -> dict:
        return {
            "provider": "SendGrid",
            "sender": self.sender,
            "recipient": self.recipient,
            "subject": message.subject,
            "status_code": response.status_code,
            "provider_message_id": response.headers.get("X-Message-Id"),
            "sent_at": datetime.now(timezone.utc).isoformat(),
        }


def send_email(api_key: str, sender: str, recipient: str, subject: str, html: str) -> dict:
    """Compatibility helper for older tests or scripts."""
    message = EmailMessage(subject=subject, html=html)
    email_sender = SendGridEmailSender(api_key=api_key, sender=sender, recipient=recipient)
    return email_sender.send(message)
