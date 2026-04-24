from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date
from typing import List, Optional

import requests

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


class BaseApiEventSource(EventSource):
    """Reusable parent class for APIs that are fetched over HTTP.

    Child classes only need to answer a few questions:
    - What URL should be called?
    - What request parameters should be sent?
    - Where are the event items inside the response?
    - How do we turn one raw item into our shared Event model?

    This is a beginner-friendly example of inheritance. The parent class owns
    the common workflow, while child classes fill in the API-specific details.
    """

    endpoint_url: str
    raw_file_name: str
    request_timeout_seconds: int = 20

    def collect_events(self, target_date: date) -> EventSourceResult:
        """Template method used by every HTTP-based event source."""
        raw_payload = self.fetch_raw_payload(target_date)
        events = self.normalize_events(raw_payload)

        return EventSourceResult(
            raw_payload=raw_payload,
            events=events,
            raw_file_name=self.raw_file_name,
        )

    def fetch_raw_payload(self, target_date: date) -> dict:
        """Call the external API and return the original JSON response."""
        response = requests.get(
            self.endpoint_url,
            params=self.build_request_params(target_date),
            timeout=self.request_timeout_seconds,
        )
        response.raise_for_status()
        return response.json()

    def normalize_events(self, payload: dict) -> List[Event]:
        """Turn the API response into our shared Event objects."""
        normalized_events: List[Event] = []

        for item in self.extract_raw_items(payload):
            event = self.normalize_item(item)
            if event is not None:
                normalized_events.append(event)

        return normalized_events

    def first_item(self, items: List[dict]) -> Optional[dict]:
        """Small helper used by several child classes."""
        return items[0] if items else None

    @abstractmethod
    def build_request_params(self, target_date: date) -> dict:
        """Return the query parameters for the external API call."""

    @abstractmethod
    def extract_raw_items(self, payload: dict) -> List[dict]:
        """Return the list of raw event items inside the API response."""

    @abstractmethod
    def normalize_item(self, item: dict) -> Optional[Event]:
        """Turn one raw API item into one Event object."""
