import logging
from datetime import date

from src.config import AppConfig
from src.services.email_service import send_email
from src.services.event_sources.ticketmaster import fetch_chicago_events, normalize_ticketmaster_events
from src.services.formatter import build_html_email, build_subject
from src.services.ranking import rank_events
from src.services.storage_service import StorageService


def run_daily_events_digest(config: AppConfig, target_date: date) -> None:
    storage = StorageService(
        account_name=config.storage_account_name,
        connection_string=config.storage_connection_string,
    )

    raw_payload = fetch_chicago_events(config.ticketmaster_api_key, target_date)
    storage.upload_json("raw-events", target_date, "ticketmaster.json", raw_payload)

    events = rank_events(normalize_ticketmaster_events(raw_payload))
    storage.upload_json(
        "processed-events",
        target_date,
        "events.json",
        [event.to_dict() for event in events],
    )

    subject = build_subject(target_date)
    html = build_html_email(events, target_date)
    send_result = send_email(
        api_key=config.sendgrid_api_key,
        sender=config.daily_email_from,
        recipient=config.daily_email_to,
        subject=subject,
        html=html,
    )
    storage.upload_json("email-logs", target_date, "send-result.json", send_result)

    logging.info("Sent Chicago Event Pulse email with %s events.", len(events))

