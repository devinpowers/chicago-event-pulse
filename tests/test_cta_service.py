from src.models.event import Event
from src.services.cta_service import CtaStation, CtaTransitService


def test_cta_service_enriches_event_with_station_and_note():
    service = StubCtaTransitService()
    event = Event(
        title="Jazz Night",
        date="2026-04-23",
        start_time="20:00:00",
        venue="Green Mill",
        address="4802 N Broadway, Chicago, IL",
        category="Music",
        price_min=20.0,
        price_max=35.0,
        url="https://example.com/jazz",
        source="Ticketmaster",
        latitude=41.9682,
        longitude=-87.6599,
    )

    result = service.enrich_events([event])

    assert result.summary == "CTA Watch: Rail lines look mostly normal this morning."
    assert result.best_pick_title == "Jazz Night"
    assert result.events[0].transit_station == "Lawrence"
    assert result.events[0].transit_score == 98
    assert "CTA Ease: Great." in result.events[0].transit_note


class StubCtaTransitService(CtaTransitService):
    def _load_stations(self):
        return [
            CtaStation(
                station_id="40770",
                station_name="Lawrence",
                descriptive_name="Lawrence (Red Line)",
                latitude=41.969139,
                longitude=-87.658493,
                line_ids=("Red",),
                line_names=("Red Line",),
            )
        ]

    def _fetch_route_statuses(self):
        return {"Red": "Normal Service"}

    def _fetch_station_alerts(self, station_id):
        return []
