from src.models.event import Event
from src.services.ranking import rank_events


def test_rank_events_sorts_by_start_time_and_limits_results():
    late = _event("Late Show", "22:00:00")
    early = _event("Morning Market", "09:00:00")
    unknown = _event("Mystery Event", None)

    ranked = rank_events([late, unknown, early], limit=2)

    assert [event.title for event in ranked] == ["Morning Market", "Late Show"]


def _event(title: str, start_time: str | None) -> Event:
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
        source="Ticketmaster",
    )

