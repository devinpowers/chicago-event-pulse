import os
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class AppConfig:
    ticketmaster_api_key: str
    sendgrid_api_key: str
    daily_email_to: str
    daily_email_from: str
    storage_account_name: str
    storage_connection_string: Optional[str] = None

    @classmethod
    def from_env(cls) -> "AppConfig":
        return cls(
            ticketmaster_api_key=_required("TICKETMASTER_API_KEY"),
            sendgrid_api_key=_required("SENDGRID_API_KEY"),
            daily_email_to=_required("DAILY_EMAIL_TO"),
            daily_email_from=_required("DAILY_EMAIL_FROM"),
            storage_account_name=_required("STORAGE_ACCOUNT_NAME"),
            storage_connection_string=os.getenv("AzureWebJobsStorage"),
        )


def _required(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required setting: {name}")
    return value
