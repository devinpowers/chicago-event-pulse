from datetime import date

from src.models.event import Event
from src.services.cta_service import TransitDigestContext
from src.services.digest_service import DailyDigestService
from src.services.event_sources.base import EventSourceResult
from src.services.formatter import EventEmailFormatter
from src.services.ranking import EventRanker


def test_daily_digest_service_combines_multiple_event_sources():
    target_date = date(2026, 4, 19)
    storage = FakeStorage()
    tables = FakeTables()
    email_sender = FakeEmailSender()

    digest_service = DailyDigestService(
        event_sources=[
            FakeEventSource("First API", "first-api.json", _event("Morning Market", "09:00:00")),
            FakeEventSource("Second API", "second-api.json", _event("Jazz Night", "20:00:00")),
        ],
        ranker=EventRanker(limit=10),
        formatter=EventEmailFormatter(),
        email_sender=email_sender,
        storage=storage,
        tables=tables,
        transit_service=FakeTransitService(),
    )

    digest = digest_service.run(target_date)

    assert digest["event_count"] == 2
    assert email_sender.sent_subject == "Today's Chicago Events - April 19, 2026"
    assert storage.uploaded_file_names == [
        "first-api.json",
        "second-api.json",
        "events.json",
        "send-result.json",
        "digest.json",
    ]


class FakeEventSource:
    def __init__(self, name, raw_file_name, event):
        self.name = name
        self.raw_file_name = raw_file_name
        self.event = event

    def collect_events(self, target_date):
        return EventSourceResult(
            raw_payload={"source": self.name, "date": target_date.isoformat()},
            events=[self.event],
            raw_file_name=self.raw_file_name,
        )


class FakeEmailSender:
    def __init__(self):
        self.sent_subject = None

    def send(self, message):
        self.sent_subject = message.subject
        return {
            "provider": "FakeEmail",
            "sender": "sender@example.com",
            "recipient": "recipient@example.com",
            "subject": message.subject,
            "status_code": 202,
            "provider_message_id": "fake-message-id",
            "sent_at": "2026-04-19T12:00:00+00:00",
        }


class FakeStorage:
    def __init__(self):
        self.uploaded_file_names = []

    def upload_json(self, container_name, target_date, file_name, payload):
        self.uploaded_file_names.append(file_name)


class FakeTables:
    def upsert_events(self, target_date, events):
        pass

    def upsert_email_log(self, target_date, send_result):
        pass

    def upsert_digest(self, target_date, digest):
        pass


class FakeTransitService:
    def enrich_events(self, events):
        enriched_events = []
        for event in events:
            enriched_events.append(
                Event(
                    title=event.title,
                    date=event.date,
                    start_time=event.start_time,
                    venue=event.venue,
                    address=event.address,
                    category=event.category,
                    price_min=event.price_min,
                    price_max=event.price_max,
                    url=event.url,
                    source=event.source,
                    event_id=event.event_id,
                    source_event_id=event.source_event_id,
                    latitude=event.latitude,
                    longitude=event.longitude,
                    transit_note="CTA Ease: Great.",
                    transit_score=90,
                )
            )

        return TransitDigestContext(
            events=enriched_events,
            summary="CTA Watch: Rail lines look mostly normal this morning.",
            best_pick_title=enriched_events[0].title if enriched_events else None,
            best_pick_note=enriched_events[0].transit_note if enriched_events else None,
        )


def _event(title, start_time):
    return Event(
        title=title,
        date="2026-04-19",
        start_time=start_time,
        venue=None,
        address=None,
        category=None,
        price_min=None,
        price_max=None,
        url=None,
        source="Fake API",
    )
