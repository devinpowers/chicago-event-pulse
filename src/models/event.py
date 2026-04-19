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

    def to_dict(self) -> dict:
        return asdict(self)
