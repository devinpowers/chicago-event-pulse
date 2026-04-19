from datetime import date, datetime, time
from zoneinfo import ZoneInfo

import requests

from src.models.event import Event

DISCOVERY_URL = "https://app.ticketmaster.com/discovery/v2/events.json"
CHICAGO_LAT_LONG = "41.8781,-87.6298"


def fetch_chicago_events(api_key: str, target_date: date) -> dict:
    start = datetime.combine(target_date, time.min, tzinfo=ZoneInfo("America/Chicago"))
    end = datetime.combine(target_date, time.max, tzinfo=ZoneInfo("America/Chicago"))

    params = {
        "apikey": api_key,
        "latlong": CHICAGO_LAT_LONG,
        "radius": "25",
        "unit": "miles",
        "startDateTime": start.astimezone(ZoneInfo("UTC")).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "endDateTime": end.astimezone(ZoneInfo("UTC")).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "sort": "date,asc",
        "size": "50",
    }

    response = requests.get(DISCOVERY_URL, params=params, timeout=20)
    response.raise_for_status()
    return response.json()


def normalize_ticketmaster_events(payload: dict) -> list[Event]:
    events = payload.get("_embedded", {}).get("events", [])
    return [event for item in events if (event := _normalize_event(item))]


def _normalize_event(item: dict) -> Event | None:
    dates = item.get("dates", {}).get("start", {})
    local_date = dates.get("localDate")
    if not local_date:
        return None

    venue = _first(item.get("_embedded", {}).get("venues", []))
    classification = _first(item.get("classifications", []))
    price_range = _first(item.get("priceRanges", []))

    return Event(
        title=item.get("name", "Untitled event"),
        date=local_date,
        start_time=dates.get("localTime"),
        venue=venue.get("name") if venue else None,
        address=_format_address(venue),
        category=_category(classification),
        price_min=price_range.get("min") if price_range else None,
        price_max=price_range.get("max") if price_range else None,
        url=item.get("url"),
        source="Ticketmaster",
        event_id=f"ticketmaster:{item.get('id')}" if item.get("id") else None,
        source_event_id=item.get("id"),
    )


def _first(items: list[dict]) -> dict | None:
    return items[0] if items else None


def _category(classification: dict | None) -> str | None:
    if not classification:
        return None

    for key in ("segment", "genre", "subGenre"):
        value = classification.get(key, {}).get("name")
        if value and value != "Undefined":
            return value

    return None


def _format_address(venue: dict | None) -> str | None:
    if not venue:
        return None

    address = venue.get("address", {}).get("line1")
    city = venue.get("city", {}).get("name")
    state = venue.get("state", {}).get("stateCode")

    parts = [part for part in (address, city, state) if part]
    return ", ".join(parts) if parts else None
