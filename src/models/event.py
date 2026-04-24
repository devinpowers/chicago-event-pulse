from dataclasses import asdict, dataclass
from typing import Optional


@dataclass(frozen=True)
class Event:
    title: str
    date: str
    start_time: Optional[str]
    venue: Optional[str]
    address: Optional[str]
    category: Optional[str]
    price_min: Optional[float]
    price_max: Optional[float]
    url: Optional[str]
    source: str
    event_id: Optional[str] = None
    source_event_id: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    transit_station: Optional[str] = None
    transit_lines: Optional[str] = None
    transit_note: Optional[str] = None
    transit_score: Optional[int] = None

    def to_dict(self) -> dict:
        return asdict(self)
