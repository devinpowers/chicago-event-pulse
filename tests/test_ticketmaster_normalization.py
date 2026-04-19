from src.services.event_sources.ticketmaster import normalize_ticketmaster_events


def test_normalize_ticketmaster_events_maps_expected_fields():
    payload = {
        "_embedded": {
            "events": [
                {
                    "name": "Chicago Bulls vs. Milwaukee Bucks",
                    "url": "https://example.com/event",
                    "dates": {"start": {"localDate": "2026-04-19", "localTime": "19:00:00"}},
                    "classifications": [{"segment": {"name": "Sports"}}],
                    "priceRanges": [{"min": 35.0, "max": 180.0}],
                    "_embedded": {
                        "venues": [
                            {
                                "name": "United Center",
                                "address": {"line1": "1901 W Madison St"},
                                "city": {"name": "Chicago"},
                                "state": {"stateCode": "IL"},
                            }
                        ]
                    },
                }
            ]
        }
    }

    events = normalize_ticketmaster_events(payload)

    assert len(events) == 1
    assert events[0].title == "Chicago Bulls vs. Milwaukee Bucks"
    assert events[0].date == "2026-04-19"
    assert events[0].venue == "United Center"
    assert events[0].address == "1901 W Madison St, Chicago, IL"
    assert events[0].category == "Sports"
    assert events[0].price_min == 35.0
    assert events[0].price_max == 180.0
    assert events[0].source == "Ticketmaster"

