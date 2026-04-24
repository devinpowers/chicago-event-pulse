from src.services.event_sources.seatgeek import SeatGeekEventSource


def test_seatgeek_normalize_events_maps_expected_fields():
    payload = {
        "events": [
            {
                "id": 12345,
                "title": "Chicago Fire FC vs. Inter Miami CF",
                "url": "https://seatgeek.example/event",
                "datetime_local": "2026-04-23T19:30:00",
                "time_tbd": False,
                "type": "sports",
                "stats": {
                    "lowest_price": 48,
                    "highest_price": 180,
                },
                "venue": {
                    "name": "Soldier Field",
                    "address": "1410 S Museum Campus Dr",
                    "city": "Chicago",
                    "state": "IL",
                    "location": {"lat": 41.8623, "lon": -87.6167},
                },
            }
        ]
    }

    source = SeatGeekEventSource(client_id="demo-client-id")
    events = source.normalize_events(payload)

    assert len(events) == 1
    assert events[0].title == "Chicago Fire FC vs. Inter Miami CF"
    assert events[0].date == "2026-04-23"
    assert events[0].start_time == "19:30:00"
    assert events[0].venue == "Soldier Field"
    assert events[0].address == "1410 S Museum Campus Dr, Chicago, IL"
    assert events[0].category == "Sports"
    assert events[0].price_min == 48
    assert events[0].price_max == 180
    assert events[0].source == "SeatGeek"
    assert events[0].latitude == 41.8623
    assert events[0].longitude == -87.6167
