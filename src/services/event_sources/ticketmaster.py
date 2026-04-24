from datetime import date, datetime, time
from typing import List, Optional
from zoneinfo import ZoneInfo

from src.models.event import Event
from src.services.event_sources.base import BaseApiEventSource

DISCOVERY_URL = "https://app.ticketmaster.com/discovery/v2/events.json"
CHICAGO_LAT_LONG = "41.8781,-87.6298"


class TicketmasterEventSource(BaseApiEventSource):
    """Gets Chicago events from the Ticketmaster Discovery API."""

    name = "Ticketmaster"
    endpoint_url = DISCOVERY_URL
    raw_file_name = "ticketmaster.json"

    def __init__(self, api_key: str) -> None:
        self.api_key = api_key

    def build_request_params(self, target_date: date) -> dict:
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

    def extract_raw_items(self, payload: dict) -> List[dict]:
        return payload.get("_embedded", {}).get("events", [])

    def normalize_item(self, item: dict) -> Optional[Event]:
        dates = item.get("dates", {}).get("start", {})
        local_date = dates.get("localDate")
        if not local_date:
            return None

        venue = self.first_item(item.get("_embedded", {}).get("venues", []))
        classification = self.first_item(item.get("classifications", []))
        price_range = self.first_item(item.get("priceRanges", []))

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
            latitude=self._float_or_none(venue.get("location", {}).get("latitude") if venue else None),
            longitude=self._float_or_none(venue.get("location", {}).get("longitude") if venue else None),
        )

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

    def _float_or_none(self, value: Optional[str]) -> Optional[float]:
        if value in (None, ""):
            return None

        try:
            return float(value)
        except (TypeError, ValueError):
            return None


def fetch_chicago_events(api_key: str, target_date: date) -> dict:
    """Compatibility helper for older tests or scripts."""
    source = TicketmasterEventSource(api_key=api_key)
    return source.fetch_raw_payload(target_date)


def normalize_ticketmaster_events(payload: dict) -> List[Event]:
    """Compatibility helper for older tests or scripts."""
    source = TicketmasterEventSource(api_key="")
    return source.normalize_events(payload)
