from datetime import date

from azure.core.exceptions import ResourceNotFoundError

from src.models.event import Event
from src.services.transit_view_service import TransitViewService, build_transit_view_html


def test_transit_view_service_builds_live_payload():
    service = TransitViewService(storage=FakeStorage(), transit_service=FakeTransitService())

    payload = service.build_view_data(date(2026, 4, 23))

    assert payload["date"] == "2026-04-23"
    assert payload["summary"] == "CTA Watch: Blue Line minor delays."
    assert payload["events"][0]["title"] == "Jazz Night"
    assert payload["events"][0]["station"]["name"] == "Division"
    assert payload["route_statuses"][0]["line_name"] == "Blue Line"
    assert payload["events"][0]["coordinates"]["latitude"] == 41.9019


def test_transit_view_html_points_to_live_data_endpoint():
    html = build_transit_view_html(date(2026, 4, 23))

    assert "Chicago transit view" in html
    assert "/api/transit-view-data?date=" in html
    assert "leaflet" in html


class FakeStorage:
    def download_json(self, container_name, target_date, file_name):
        if container_name == "processed-events":
            assert file_name == "events.json"
            return [
                Event(
                    title="Jazz Night",
                    date="2026-04-23",
                    start_time="20:00:00",
                    venue="Empty Bottle",
                    address="1035 N Western Ave, Chicago, IL",
                    category="Music",
                    price_min=20.0,
                    price_max=25.0,
                    url="https://example.com/jazz",
                    source="Ticketmaster",
                    source_event_id="tm-123",
                ).to_dict()
            ]

        if container_name == "raw-events":
            if file_name == "seatgeek.json":
                raise ResourceNotFoundError("missing")

            assert file_name == "ticketmaster.json"
            return {
                "_embedded": {
                    "events": [
                        {
                            "id": "tm-123",
                            "name": "Jazz Night",
                            "url": "https://example.com/jazz",
                            "dates": {"start": {"localDate": "2026-04-23", "localTime": "20:00:00"}},
                            "_embedded": {
                                "venues": [
                                    {
                                        "name": "Empty Bottle",
                                        "address": {"line1": "1035 N Western Ave"},
                                        "city": {"name": "Chicago"},
                                        "state": {"stateCode": "IL"},
                                        "location": {"latitude": "41.9019", "longitude": "-87.6873"},
                                    }
                                ]
                            },
                        }
                    ]
                }
            }

        raise AssertionError(f"unexpected blob request: {container_name}/{file_name}")


class FakeTransitService:
    def enrich_events(self, events):
        return type("TransitContext", (), {"events": events})()

    def build_map_data(self, events):
        return type(
            "MapData",
            (),
            {
                "generated_at": "2026-04-23T12:00:00+00:00",
                "summary": "CTA Watch: Blue Line minor delays.",
                "route_statuses": [
                    {"line_id": "Blue", "line_name": "Blue Line", "status": "Minor Delays"},
                ],
                "events": [
                    {
                        "title": events[0].title,
                        "coordinates": {"latitude": events[0].latitude, "longitude": events[0].longitude},
                        "price_min": 20.0,
                        "price_max": 25.0,
                        "station": {
                            "name": "Division",
                            "lines": ["Blue Line"],
                            "coordinates": {"latitude": 41.903355, "longitude": -87.666496},
                            "line_statuses": [{"line": "Blue Line", "status": "Minor Delays"}],
                            "walk_minutes": 8,
                            "alerts": [],
                        },
                        "transit_note": "CTA Ease: Solid. About 8 min to Division; Blue Line minor delays",
                        "venue": events[0].venue,
                        "start_time": events[0].start_time,
                        "url": events[0].url,
                    }
                ],
            },
        )()
