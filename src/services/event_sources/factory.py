from typing import List

from src.config import AppConfig
from src.services.event_sources.base import EventSource
from src.services.event_sources.ticketmaster import TicketmasterEventSource


class EventSourceFactory:
    """Builds the list of event sources used by the application.

    Right now we only have Ticketmaster. Later this factory can add more APIs
    without forcing the digest workflow to change.
    """

    @staticmethod
    def build_sources(config: AppConfig) -> List[EventSource]:
        return [
            TicketmasterEventSource(api_key=config.ticketmaster_api_key),
        ]
