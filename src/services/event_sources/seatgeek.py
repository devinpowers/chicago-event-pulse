from datetime import date, datetime, time
from typing import List, Optional
from zoneinfo import ZoneInfo

from src.models.event import Event
from src.services.event_sources.base import BaseApiEventSource

SEATGEEK_EVENTS_URL = "https://api.seatgeek.com/2/events"


class SeatGeekEventSource(BaseApiEventSource):
    """Gets Chicago events from the SeatGeek Platform API."""

    name = "SeatGeek"
    endpoint_url = SEATGEEK_EVENTS_URL
    raw_file_name = "seatgeek.json"

    def __init__(self, client_id: str) -> None:
        self.client_id = client_id

    def build_request_params(self, target_date: date) -> dict:
        start = datetime.combine(target_date, time.min, tzinfo=ZoneInfo("America/Chicago"))
        end = datetime.combine(target_date, time.max, tzinfo=ZoneInfo("America/Chicago"))

        return {
            "client_id": self.client_id,
            "venue.city": "chicago",
            "venue.state": "IL",
            "datetime_local.gte": start.strftime("%Y-%m-%dT%H:%M:%S"),
            "datetime_local.lte": end.strftime("%Y-%m-%dT%H:%M:%S"),
            "sort": "datetime_local.asc",
            "per_page": "50",
        }

    def extract_raw_items(self, payload: dict) -> List[dict]:
        return payload.get("events", [])

    def normalize_item(self, item: dict) -> Optional[Event]:
        local_datetime = item.get("datetime_local")
        if not local_datetime:
            return None

        date_text, _, time_text = local_datetime.partition("T")
        start_time = None if item.get("time_tbd") else (time_text or None)

        venue = item.get("venue") or {}
        stats = item.get("stats") or {}

        return Event(
            title=item.get("title") or item.get("short_title") or "Untitled event",
            date=date_text,
            start_time=start_time,
            venue=venue.get("name"),
            address=self._format_address(venue),
            category=self._category(item),
            price_min=stats.get("lowest_price"),
            price_max=stats.get("highest_price"),
            url=item.get("url"),
            source=self.name,
            event_id=f"seatgeek:{item.get('id')}" if item.get("id") else None,
            source_event_id=str(item.get("id")) if item.get("id") else None,
            latitude=self._float_or_none(venue.get("location", {}).get("lat") or venue.get("lat")),
            longitude=self._float_or_none(venue.get("location", {}).get("lon") or venue.get("lon")),
        )

    def _category(self, item: dict) -> Optional[str]:
        if item.get("type"):
            return item["type"].title()

        taxonomies = item.get("taxonomies") or []
        first_taxonomy = self.first_item(taxonomies)
        if first_taxonomy and first_taxonomy.get("name"):
            return str(first_taxonomy["name"]).title()

        return None

    def _format_address(self, venue: dict) -> Optional[str]:
        address = venue.get("address")
        city = venue.get("city")
        state = venue.get("state")

        parts = [part for part in (address, city, state) if part]
        return ", ".join(parts) if parts else None

    def _float_or_none(self, value: Optional[float]) -> Optional[float]:
        if value in (None, ""):
            return None

        try:
            return float(value)
        except (TypeError, ValueError):
            return None
