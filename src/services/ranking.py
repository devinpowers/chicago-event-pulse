from typing import List, Tuple

from src.models.event import Event


def rank_events(events: List[Event], limit: int = 10) -> List[Event]:
    return sorted(events, key=_sort_key)[:limit]


def _sort_key(event: Event) -> Tuple[str, str, str]:
    return (
        event.start_time or "99:99:99",
        event.category or "zzzz",
        event.title.lower(),
    )
