import logging
import math
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from typing import Dict, Iterable, List, Optional, Sequence

import requests

from src.models.event import Event

CTA_STOPS_URL = "https://data.cityofchicago.org/resource/8pix-ypme.json"
CTA_ALERTS_URL = "https://www.transitchicago.com/api/1.0/alerts.aspx"
CTA_ROUTE_STATUS_URL = "https://lapi.transitchicago.com/api/1.0/routes.aspx"
MAX_WALKABLE_DISTANCE_MILES = 1.25

LINE_FIELD_MAP = {
    "red": ("Red", "Red Line"),
    "blue": ("Blue", "Blue Line"),
    "brn": ("Brn", "Brown Line"),
    "g": ("G", "Green Line"),
    "o": ("Org", "Orange Line"),
    "p": ("P", "Purple Line"),
    "pnk": ("Pink", "Pink Line"),
    "y": ("Y", "Yellow Line"),
}

STATUS_PRIORITY = {
    "Normal Service": 0,
    "See Alert": 1,
    "Planned Work": 2,
    "Service Change": 2,
    "Minor Delays": 3,
    "Major Delays": 4,
    "Service Disruption": 5,
    "Service Suspended": 6,
}


@dataclass(frozen=True)
class TransitDigestContext:
    events: List[Event]
    summary: Optional[str] = None
    best_pick_title: Optional[str] = None
    best_pick_note: Optional[str] = None


@dataclass(frozen=True)
class CtaStation:
    station_id: str
    station_name: str
    descriptive_name: str
    latitude: float
    longitude: float
    line_ids: Sequence[str]
    line_names: Sequence[str]


@dataclass(frozen=True)
class TransitMapData:
    generated_at: str
    summary: str
    route_statuses: List[dict]
    events: List[dict]


class CtaTransitService:
    """Adds CTA context to ranked events right before the email is built."""

    request_timeout_seconds = 20

    def __init__(self) -> None:
        self._stations_cache: Optional[List[CtaStation]] = None

    def enrich_events(self, events: List[Event]) -> TransitDigestContext:
        if not events:
            return TransitDigestContext(events=events)

        try:
            route_statuses = self._fetch_route_statuses()
            stations = self._load_stations()
        except Exception:
            logging.exception("CTA transit enrichment unavailable during setup.")
            return TransitDigestContext(events=events)

        alert_cache: Dict[str, List[dict]] = {}
        enriched_events: List[Event] = []

        for event in events:
            if event.latitude is None or event.longitude is None:
                enriched_events.append(event)
                continue

            station, distance_miles = self._nearest_station(event.latitude, event.longitude, stations)
            if station is None or distance_miles > MAX_WALKABLE_DISTANCE_MILES:
                enriched_events.append(
                    replace(
                        event,
                        transit_note="CTA Ease: Limited. No nearby rail stop found.",
                        transit_score=25,
                    )
                )
                continue

            alerts = alert_cache.get(station.station_id)
            if alerts is None:
                try:
                    alerts = self._fetch_station_alerts(station.station_id)
                except Exception:
                    logging.exception("CTA station alerts unavailable for %s.", station.station_id)
                    alerts = []
                alert_cache[station.station_id] = alerts

            line_statuses = self._line_statuses_for_station(station, route_statuses)
            transit_score = self._score_station(distance_miles, line_statuses, alerts)
            transit_note = self._build_transit_note(station, distance_miles, line_statuses, alerts)

            enriched_events.append(
                replace(
                    event,
                    transit_station=station.station_name,
                    transit_lines=", ".join(station.line_names),
                    transit_note=transit_note,
                    transit_score=transit_score,
                )
            )

        best_pick = self._best_pick(enriched_events)
        return TransitDigestContext(
            events=enriched_events,
            summary=self._build_summary(route_statuses),
            best_pick_title=best_pick.title if best_pick else None,
            best_pick_note=best_pick.transit_note if best_pick else None,
        )

    def build_map_data(self, events: List[Event]) -> TransitMapData:
        try:
            route_statuses = self._fetch_route_statuses()
            stations = self._load_stations()
        except Exception:
            logging.exception("CTA transit map unavailable during setup.")
            return TransitMapData(
                generated_at=datetime.now(timezone.utc).isoformat(),
                summary="CTA data is unavailable right now.",
                route_statuses=[],
                events=[self._event_payload(event, None, None, [], []) for event in events],
            )

        alert_cache: Dict[str, List[dict]] = {}
        map_events = []

        for event in events:
            station = None
            distance_miles = None
            alerts: List[dict] = []
            line_statuses: List[tuple[str, str]] = []

            if event.latitude is not None and event.longitude is not None:
                station, distance_miles = self._nearest_station(event.latitude, event.longitude, stations)
                if station is not None and distance_miles <= MAX_WALKABLE_DISTANCE_MILES:
                    alerts = alert_cache.get(station.station_id)
                    if alerts is None:
                        try:
                            alerts = self._fetch_station_alerts(station.station_id)
                        except Exception:
                            logging.exception("CTA station alerts unavailable for %s.", station.station_id)
                            alerts = []
                        alert_cache[station.station_id] = alerts

                    line_statuses = self._line_statuses_for_station(station, route_statuses)

            map_events.append(self._event_payload(event, station, distance_miles, line_statuses, alerts))

        return TransitMapData(
            generated_at=datetime.now(timezone.utc).isoformat(),
            summary=self._build_summary(route_statuses) or "CTA Watch unavailable.",
            route_statuses=self._route_status_payload(route_statuses),
            events=map_events,
        )

    def _load_stations(self) -> List[CtaStation]:
        if self._stations_cache is not None:
            return self._stations_cache

        response = requests.get(
            CTA_STOPS_URL,
            params={"$limit": 400},
            timeout=self.request_timeout_seconds,
        )
        response.raise_for_status()

        stations_by_id: Dict[str, CtaStation] = {}
        for item in response.json():
            station_id = item.get("map_id")
            location = item.get("location") or {}
            latitude = self._float_or_none(location.get("latitude"))
            longitude = self._float_or_none(location.get("longitude"))
            if not station_id or latitude is None or longitude is None:
                continue

            line_ids: List[str] = []
            line_names: List[str] = []
            for field, (line_id, line_name) in LINE_FIELD_MAP.items():
                if item.get(field):
                    line_ids.append(line_id)
                    line_names.append(line_name)

            if not line_ids:
                continue

            stations_by_id[station_id] = CtaStation(
                station_id=station_id,
                station_name=item.get("station_name") or "CTA station",
                descriptive_name=item.get("station_descriptive_name") or item.get("station_name") or "CTA station",
                latitude=latitude,
                longitude=longitude,
                line_ids=tuple(line_ids),
                line_names=tuple(line_names),
            )

        self._stations_cache = list(stations_by_id.values())
        return self._stations_cache

    def _fetch_route_statuses(self) -> Dict[str, str]:
        response = requests.get(
            CTA_ROUTE_STATUS_URL,
            params={"outputType": "JSON"},
            timeout=self.request_timeout_seconds,
        )
        response.raise_for_status()
        payload = response.json().get("CTARoutes", {})
        route_info = payload.get("RouteInfo") or []
        if isinstance(route_info, dict):
            route_info = [route_info]

        statuses: Dict[str, str] = {}
        for item in route_info:
            service_id = item.get("ServiceId")
            status = item.get("RouteStatus")
            if service_id and status and service_id in {line_id for line_id, _ in LINE_FIELD_MAP.values()}:
                statuses[service_id] = status

        return statuses

    def _fetch_station_alerts(self, station_id: str) -> List[dict]:
        response = requests.get(
            CTA_ALERTS_URL,
            params={
                "activeonly": "true",
                "stationid": station_id,
                "accessibility": "false",
                "outputType": "JSON",
            },
            timeout=self.request_timeout_seconds,
        )
        response.raise_for_status()
        alerts = response.json().get("CTAAlerts", {}).get("Alert") or []
        if isinstance(alerts, dict):
            return [alerts]
        return alerts

    def _nearest_station(
        self,
        latitude: float,
        longitude: float,
        stations: Iterable[CtaStation],
    ) -> tuple[Optional[CtaStation], float]:
        best_station: Optional[CtaStation] = None
        best_distance = float("inf")

        for station in stations:
            distance = self._miles_between(latitude, longitude, station.latitude, station.longitude)
            if distance < best_distance:
                best_station = station
                best_distance = distance

        return best_station, best_distance

    def _line_statuses_for_station(
        self,
        station: CtaStation,
        route_statuses: Dict[str, str],
    ) -> List[tuple[str, str]]:
        statuses = []
        for line_id, line_name in zip(station.line_ids, station.line_names):
            status = route_statuses.get(line_id, "Status unavailable")
            statuses.append((line_name, status))
        return statuses

    def _build_summary(self, route_statuses: Dict[str, str]) -> Optional[str]:
        flagged = []
        for _, (service_id, line_name) in LINE_FIELD_MAP.items():
            status = route_statuses.get(service_id)
            if status and status != "Normal Service":
                flagged.append(f"{line_name}: {status}")

        if not flagged:
            return "CTA Watch: Rail lines look mostly normal this morning."

        return "CTA Watch: " + "; ".join(flagged[:3]) + "."

    def _build_transit_note(
        self,
        station: CtaStation,
        distance_miles: float,
        line_statuses: List[tuple[str, str]],
        alerts: List[dict],
    ) -> str:
        walk_minutes = max(1, round(distance_miles * 20))
        best_line_name, best_status = min(
            line_statuses,
            key=lambda item: STATUS_PRIORITY.get(item[1], 99),
        )

        line_summary = self._line_summary(line_statuses)
        if alerts:
            headline = alerts[0].get("Headline") or alerts[0].get("ShortDescription")
            return f"CTA Ease: Mixed. About {walk_minutes} min to {station.station_name}; {line_summary}; {headline}"

        if best_status == "Normal Service":
            return f"CTA Ease: Great. About {walk_minutes} min to {station.station_name}; {line_summary}"

        if STATUS_PRIORITY.get(best_status, 99) >= STATUS_PRIORITY["Major Delays"]:
            return f"CTA Ease: Tough. About {walk_minutes} min to {station.station_name}; {line_summary}"

        return f"CTA Ease: Solid. About {walk_minutes} min to {station.station_name}; {line_summary}"

    def _line_summary(self, line_statuses: List[tuple[str, str]]) -> str:
        normal_lines = [line_name for line_name, status in line_statuses if status == "Normal Service"]
        flagged_lines = [f"{line_name} {status.lower()}" for line_name, status in line_statuses if status != "Normal Service"]

        parts = []
        if normal_lines:
            parts.append(f"{', '.join(normal_lines)} normal")
        if flagged_lines:
            parts.append(", ".join(flagged_lines))
        return "; ".join(parts)

    def _score_station(
        self,
        distance_miles: float,
        line_statuses: List[tuple[str, str]],
        alerts: List[dict],
    ) -> int:
        best_line_penalty = min(STATUS_PRIORITY.get(status, 6) * 10 for _, status in line_statuses)
        score = 100
        score -= min(35, round(distance_miles * 25))
        score -= best_line_penalty
        if alerts:
            score -= 15
        return max(0, score)

    def _event_payload(
        self,
        event: Event,
        station: Optional[CtaStation],
        distance_miles: Optional[float],
        line_statuses: List[tuple[str, str]],
        alerts: List[dict],
    ) -> dict:
        walk_minutes = None if distance_miles is None else max(1, round(distance_miles * 20))

        return {
            "title": event.title,
            "category": event.category,
            "venue": event.venue,
            "address": event.address,
            "start_time": event.start_time,
            "date": event.date,
            "url": event.url,
            "price_min": event.price_min,
            "price_max": event.price_max,
            "transit_note": event.transit_note,
            "transit_score": event.transit_score,
            "coordinates": self._coordinates_payload(event.latitude, event.longitude),
            "station": None
            if station is None or distance_miles is None or distance_miles > MAX_WALKABLE_DISTANCE_MILES
            else {
                "id": station.station_id,
                "name": station.station_name,
                "description": station.descriptive_name,
                "coordinates": self._coordinates_payload(station.latitude, station.longitude),
                "lines": list(station.line_names),
                "line_statuses": [
                    {"line": line_name, "status": status}
                    for line_name, status in line_statuses
                ],
                "walk_minutes": walk_minutes,
                "alerts": [
                    {
                        "headline": alert.get("Headline") or alert.get("ShortDescription"),
                        "impact": alert.get("Impact"),
                        "major_alert": alert.get("MajorAlert") == "1",
                    }
                    for alert in alerts[:3]
                ],
            },
        }

    def _route_status_payload(self, route_statuses: Dict[str, str]) -> List[dict]:
        payload = []
        for _, (service_id, line_name) in LINE_FIELD_MAP.items():
            status = route_statuses.get(service_id, "Status unavailable")
            payload.append(
                {
                    "line_id": service_id,
                    "line_name": line_name,
                    "status": status,
                }
            )
        return payload

    def _coordinates_payload(self, latitude: Optional[float], longitude: Optional[float]) -> Optional[dict]:
        if latitude is None or longitude is None:
            return None
        return {"latitude": latitude, "longitude": longitude}

    def _best_pick(self, events: List[Event]) -> Optional[Event]:
        candidates = [event for event in events if event.transit_score is not None and event.transit_note]
        if not candidates:
            return None
        return max(candidates, key=lambda event: (event.transit_score or 0, event.start_time or "99:99:99"))

    def _miles_between(
        self,
        lat_one: float,
        lon_one: float,
        lat_two: float,
        lon_two: float,
    ) -> float:
        radius_miles = 3958.8
        lat_one_rad = math.radians(lat_one)
        lat_two_rad = math.radians(lat_two)
        delta_lat = math.radians(lat_two - lat_one)
        delta_lon = math.radians(lon_two - lon_one)

        a = (
            math.sin(delta_lat / 2) ** 2
            + math.cos(lat_one_rad) * math.cos(lat_two_rad) * math.sin(delta_lon / 2) ** 2
        )
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return radius_miles * c

    def _float_or_none(self, value: Optional[str]) -> Optional[float]:
        if value in (None, ""):
            return None

        try:
            return float(value)
        except (TypeError, ValueError):
            return None
