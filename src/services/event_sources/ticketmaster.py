from datetime import date, datetime, time
from typing import Dict, List, Optional
from zoneinfo import ZoneInfo

import requests

from src.models.event import Event
from src.services.event_sources.base import EventSource, EventSourceResult

DISCOVERY_URL = "https://app.ticketmaster.com/discovery/v2/events.json"
CHICAGO_LAT_LONG = "41.8781,-87.6298"


class TicketmasterEventSource(EventSource):
    """Gets Chicago events from the Ticketmaster Discovery API."""

    name = "Ticketmaster"

    def __init__(self, api_key: str) -> None:
        self.api_key = api_key

    def collect_events(self, target_date: date) -> EventSourceResult:
        raw_payload = self.fetch_raw_payload(target_date)
        events = self.normalize_events(raw_payload)

        return EventSourceResult(
            raw_payload=raw_payload,
            events=events,
            raw_file_name="ticketmaster.json",
        )

    def fetch_raw_payload(self, target_date: date) -> dict:
        params = self._build_request_params(target_date)
        response = requests.get(DISCOVERY_URL, params=params, timeout=20)
        response.raise_for_status()
        return response.json()

    def normalize_events(self, payload: dict) -> List[Event]:
        events = payload.get("_embedded", {}).get("events", [])
        normalized_events = []

        for item in events:
            event = self._normalize_event(item)
            if event:
                normalized_events.append(event)

        return normalized_events

    def _build_request_params(self, target_date: date) -> dict:
        start = datetime.combine(target_date, time.min, tzinfo=ZoneInfo("America/Chicago"))
        end = datetime.combine(target_date, time.max, tzinfo=ZoneInfo("America/Chicago"))

        return {
            "apikey": self.api_key,
            "latlong": CHICAGO_LAT_LONG,
            "radius": "25",
            "unit": "miles",
            "startDateTime": start.astimezone(ZoneInfo("UTC")).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "endDateTime": end.astimezone(ZoneInfo("UTC")).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "sort": "date,asc",
            "size": "50",
        }

    def _normalize_event(self, item: dict) -> Optional[Event]:
        dates = item.get("dates", {}).get("start", {})
        local_date = dates.get("localDate")
        if not local_date:
            return None

        venue = self._first(item.get("_embedded", {}).get("venues", []))
        classification = self._first(item.get("classifications", []))
        price_range = self._first(item.get("priceRanges", []))

        return Event(
            title=item.get("name", "Untitled event"),
            date=local_date,
            start_time=dates.get("localTime"),
            venue=venue.get("name") if venue else None,
            address=self._format_address(venue),
            category=self._category(classification),
            price_min=price_range.get("min") if price_range else None,
            price_max=price_range.get("max") if price_range else None,
            url=item.get("url"),
            source=self.name,
            event_id=f"ticketmaster:{item.get('id')}" if item.get("id") else None,
            source_event_id=item.get("id"),
        )

    def _first(self, items: List[Dict]) -> Optional[Dict]:
        return items[0] if items else None

    def _category(self, classification: Optional[dict]) -> Optional[str]:
        if not classification:
            return None

        for key in ("segment", "genre", "subGenre"):
            value = classification.get(key, {}).get("name")
            if value and value != "Undefined":
                return value

        return None

    def _format_address(self, venue: Optional[dict]) -> Optional[str]:
        if not venue:
            return None

        address = venue.get("address", {}).get("line1")
        city = venue.get("city", {}).get("name")
        state = venue.get("state", {}).get("stateCode")

        parts = [part for part in (address, city, state) if part]
        return ", ".join(parts) if parts else None


def fetch_chicago_events(api_key: str, target_date: date) -> dict:
    """Compatibility helper for older tests or scripts."""
    source = TicketmasterEventSource(api_key=api_key)
    return source.fetch_raw_payload(target_date)


def normalize_ticketmaster_events(payload: dict) -> List[Event]:
    """Compatibility helper for older tests or scripts."""
    source = TicketmasterEventSource(api_key="")
    return source.normalize_events(payload)
