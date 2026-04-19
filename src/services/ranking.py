from typing import List, Tuple

from src.models.event import Event


class EventRanker:
    """Chooses which events should appear in the email first."""

    def __init__(self, limit: int = 10) -> None:
        self.limit = limit

    def rank(self, events: List[Event]) -> List[Event]:
        return sorted(events, key=self._sort_key)[: self.limit]

    def _sort_key(self, event: Event) -> Tuple[str, str, str]:
        return (
            event.start_time or "99:99:99",
            event.category or "zzzz",
            event.title.lower(),
        )


def rank_events(events: List[Event], limit: int = 10) -> List[Event]:
    """Compatibility helper for older tests or scripts."""
    return EventRanker(limit=limit).rank(events)
