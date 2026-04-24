import logging
from datetime import date, datetime, timezone
from typing import List

from src.config import AppConfig
from src.models.event import Event
from src.services.cta_service import CtaTransitService
from src.services.email_service import SendGridEmailSender
from src.services.event_sources.base import EventSource
from src.services.event_sources.factory import EventSourceFactory
from src.services.formatter import EventEmailFormatter
from src.services.ranking import EventRanker
from src.services.storage_service import StorageService
from src.services.table_service import TableStorageService


class DailyDigestService:
    """Coordinates one full daily digest run.

    This class is the main application workflow. It does not know the details of
    Ticketmaster, SendGrid, Blob Storage, or Table Storage. It only asks smaller
    components to do their jobs in order.
    """

    def __init__(
        self,
        event_sources: List[EventSource],
        ranker: EventRanker,
        formatter: EventEmailFormatter,
        email_sender: SendGridEmailSender,
        storage: StorageService,
        tables: TableStorageService,
        transit_service: CtaTransitService | None = None,
    ) -> None:
        self.event_sources = event_sources
        self.ranker = ranker
        self.formatter = formatter
        self.email_sender = email_sender
        self.storage = storage
        self.tables = tables
        self.transit_service = transit_service or CtaTransitService()

    @classmethod
    def from_config(cls, config: AppConfig) -> "DailyDigestService":
        """Create the production version of the digest service."""
        storage = StorageService(
            account_name=config.storage_account_name,
            connection_string=config.storage_connection_string,
        )
        tables = TableStorageService(
            account_name=config.storage_account_name,
            connection_string=config.storage_connection_string,
        )

        return cls(
            event_sources=EventSourceFactory.build_sources(config),
            ranker=EventRanker(limit=10),
            formatter=EventEmailFormatter(),
            email_sender=SendGridEmailSender(
                api_key=config.sendgrid_api_key,
                sender=config.daily_email_from,
                recipient=config.daily_email_to,
            ),
            storage=storage,
            tables=tables,
            transit_service=CtaTransitService(),
        )

    def run(self, target_date: date) -> dict:
        """Fetch events, send the email, store the result, and return a summary."""
        events, raw_blob_paths = self._fetch_events_from_all_sources(target_date)
        ranked_events = self.ranker.rank(events)
        transit_context = self.transit_service.enrich_events(ranked_events)
        ranked_events = transit_context.events

        self._save_events(target_date, ranked_events)

        email_message = self.formatter.build_message(
            ranked_events,
            target_date,
            transit_summary=transit_context.summary,
            transit_pick_title=transit_context.best_pick_title,
            transit_pick_note=transit_context.best_pick_note,
        )
        send_result = self.email_sender.send(email_message)
        self._save_email_result(target_date, send_result)

        digest = self._build_digest_summary(target_date, ranked_events, raw_blob_paths)
        self._save_digest_summary(target_date, digest)

        logging.info("Sent Chicago Event Pulse email with %s events.", len(ranked_events))
        return digest

    def _fetch_events_from_all_sources(self, target_date: date) -> tuple[List[Event], List[str]]:
        all_events: List[Event] = []
        raw_blob_paths: List[str] = []

        for source in self.event_sources:
            result = source.collect_events(target_date)
            self.storage.upload_json("raw-events", target_date, result.raw_file_name, result.raw_payload)
            all_events.extend(result.events)
            raw_blob_paths.append(f"raw-events/{target_date:%Y/%m/%d}/{result.raw_file_name}")

        return all_events, raw_blob_paths

    def _save_events(self, target_date: date, events: List[Event]) -> None:
        self.storage.upload_json(
            "processed-events",
            target_date,
            "events.json",
            [event.to_dict() for event in events],
        )
        self.tables.upsert_events(target_date, events)

    def _save_email_result(self, target_date: date, send_result: dict) -> None:
        self.storage.upload_json("email-logs", target_date, "send-result.json", send_result)
        self.tables.upsert_email_log(target_date, send_result)

    def _build_digest_summary(
        self,
        target_date: date,
        events: List[Event],
        raw_blob_paths: List[str],
    ) -> dict:
        digest = {
            "digest_date": target_date.isoformat(),
            "city": "Chicago",
            "timezone": "America/Chicago",
            "status": "sent",
            "event_count": len(events),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "processed_blob_path": f"processed-events/{target_date:%Y/%m/%d}/events.json",
            "email_log_blob_path": f"email-logs/{target_date:%Y/%m/%d}/send-result.json",
        }

        if len(raw_blob_paths) == 1:
            digest["raw_blob_path"] = raw_blob_paths[0]
        else:
            digest["raw_blob_paths"] = raw_blob_paths

        return digest

    def _save_digest_summary(self, target_date: date, digest: dict) -> None:
        self.storage.upload_json("processed-events", target_date, "digest.json", digest)
        self.tables.upsert_digest(target_date, digest)
