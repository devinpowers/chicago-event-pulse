from datetime import date

from src.models.event import Event
from src.services.formatter import build_html_email, build_subject


def test_build_subject_uses_target_date():
    assert build_subject(date(2026, 4, 19)) == "Today's Chicago Events - April 19, 2026"


def test_build_html_email_contains_event_details():
    event = Event(
        title="Jazz Night",
        date="2026-04-19",
        start_time="20:00:00",
        venue="Green Mill",
        address="4802 N Broadway, Chicago, IL",
        category="Music",
        price_min=15.0,
        price_max=20.0,
        url="https://example.com/jazz",
        source="Ticketmaster",
    )

    html = build_html_email([event], date(2026, 4, 19))

    assert "Jazz Night" in html
    assert "Green Mill" in html
    assert "20:00:00" in html
    assert "$15-$20" in html
    assert "https://example.com/jazz" in html

