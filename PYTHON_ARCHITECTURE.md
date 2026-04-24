# Python OOP Architecture

This MVP is organized around small classes with clear jobs. The goal is to make
the code easy to read and easy to extend when we add more event APIs.

## Main Flow

The Azure Function calls:

```text
run_daily_events_digest()
  -> DailyDigestService.run()
```

`DailyDigestService` is the coordinator. It does the daily workflow in this
order:

1. Ask each event source for events.
2. Save each source's raw API response to Blob Storage.
3. Rank the combined events.
4. Save the processed events to Blob Storage and Table Storage.
5. Build the email.
6. Send the email.
7. Save the email result.
8. Save the digest summary.

## Important Classes

### `DailyDigestService`

File: `src/services/digest_service.py`

This is the main workflow class. It does not know the details of Ticketmaster,
SendGrid, or Azure Storage. It asks smaller objects to do those jobs.

### `EventSource`

File: `src/services/event_sources/base.py`

This is the shape every event API should follow. Each event source returns an
`EventSourceResult`, which contains:

- `raw_payload`: the original API response
- `events`: normalized `Event` objects
- `raw_file_name`: the file name to use in Blob Storage

### `BaseApiEventSource`

File: `src/services/event_sources/base.py`

This is the parent class for event APIs that use HTTP requests. It owns the
shared workflow:

1. call the API
2. get the raw JSON
3. find the raw event items
4. normalize each item into an `Event`
5. return an `EventSourceResult`

Child classes only fill in the API-specific pieces. This is the main parent /
child relationship in the project.

### `TicketmasterEventSource`

File: `src/services/event_sources/ticketmaster.py`

This is our first child class. It inherits from `BaseApiEventSource`.

It knows how to:

- call the Ticketmaster Discovery API
- normalize the Ticketmaster response into our shared `Event` model
- return both raw and normalized data

### `EventSourceFactory`

File: `src/services/event_sources/factory.py`

This class decides which event sources the app should use. Right now it returns
only Ticketmaster. Later it can add more APIs in one place.

### `Event`

File: `src/models/event.py`

This is the shared event shape used by the whole app. Every API should convert
its own response into this model.

### `EventRanker`

File: `src/services/ranking.py`

This chooses which events show up first in the email.

### `EventEmailFormatter`

File: `src/services/formatter.py`

This turns events into an email subject and HTML body.

### `SendGridEmailSender`

File: `src/services/email_service.py`

This sends the prepared email through SendGrid.

## How To Add Another Event API

1. Create a new file in `src/services/event_sources/`.
2. Create a child class that inherits from `BaseApiEventSource`.
3. Implement the API-specific methods:
   - `build_request_params()`
   - `extract_raw_items()`
   - `normalize_item()`
4. Convert that API response into `Event` objects.
5. Add the new source to `EventSourceFactory.build_sources()`.

Example shape:

```python
class NewApiEventSource(BaseApiEventSource):
    name = "New API"
    endpoint_url = "https://example.com/events"
    raw_file_name = "new-api.json"

    def build_request_params(self, target_date):
        return {"date": target_date.isoformat()}

    def extract_raw_items(self, payload):
        return payload.get("events", [])

    def normalize_item(self, item):
        return Event(...)
```

Once the new source is added to `EventSourceFactory.build_sources()`, the rest of
the app can use it without changing the email, ranking, storage, or function
trigger code.
