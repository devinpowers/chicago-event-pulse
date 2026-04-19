from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date
from typing import List

from src.models.event import Event


@dataclass(frozen=True)
class EventSourceResult:
    """The output from one event API.

    raw_payload is the original API response we save for debugging.
    events is the clean list our app uses for ranking and email formatting.
    raw_file_name is the blob file name for this source's raw response.
    """

    raw_payload: dict
    events: List[Event]
    raw_file_name: str


class EventSource(ABC):
    """A provider that can return events for one day.

    Each external API gets its own EventSource class. The digest runner can then
    combine several sources without needing to know how each API works.
    """

    name: str

    @abstractmethod
    def collect_events(self, target_date: date) -> EventSourceResult:
        """Return raw and normalized event data for the requested day."""
