from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class Event:
    title: str
    date: str
    start_time: str | None
    venue: str | None
    address: str | None
    category: str | None
    price_min: float | None
    price_max: float | None
    url: str | None
    source: str
    event_id: str | None = None
    source_event_id: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)
