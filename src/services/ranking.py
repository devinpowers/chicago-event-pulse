from src.models.event import Event


def rank_events(events: list[Event], limit: int = 10) -> list[Event]:
    return sorted(events, key=_sort_key)[:limit]


def _sort_key(event: Event) -> tuple[str, str, str]:
    return (
        event.start_time or "99:99:99",
        event.category or "zzzz",
        event.title.lower(),
    )

