from datetime import datetime, timezone

import requests


SENDGRID_URL = "https://api.sendgrid.com/v3/mail/send"


def send_email(api_key: str, sender: str, recipient: str, subject: str, html: str) -> dict:
    payload = {
        "personalizations": [{"to": [{"email": recipient}]}],
        "from": {"email": sender},
        "subject": subject,
        "content": [{"type": "text/html", "value": html}],
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    response = requests.post(SENDGRID_URL, json=payload, headers=headers, timeout=20)
    response.raise_for_status()

    return {
        "provider": "SendGrid",
        "sender": sender,
        "recipient": recipient,
        "subject": subject,
        "status_code": response.status_code,
        "provider_message_id": response.headers.get("X-Message-Id"),
        "sent_at": datetime.now(timezone.utc).isoformat(),
    }
