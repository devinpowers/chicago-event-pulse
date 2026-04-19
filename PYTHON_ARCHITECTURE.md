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

### `TicketmasterEventSource`

File: `src/services/event_sources/ticketmaster.py`

This is our first event API. It knows how to:

- call the Ticketmaster Discovery API
- normalize the Ticketmaster response into our shared `Event` model
- return both raw and normalized data

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
2. Create a class that follows `EventSource`.
3. In that class, call the external API.
4. Convert that API response into a list of `Event` objects.
5. Return an `EventSourceResult`.
6. Add the new source to the list in `DailyDigestService.from_config()`.

Example shape:

```python
class NewApiEventSource(EventSource):
    name = "New API"

    def collect_events(self, target_date):
        raw_payload = self.fetch_raw_payload(target_date)
        events = self.normalize_events(raw_payload)

        return EventSourceResult(
            raw_payload=raw_payload,
            events=events,
            raw_file_name="new-api.json",
        )
```

Once the new source is added to `DailyDigestService.from_config()`, the rest of
the app can use it without changing the email, ranking, storage, or function
trigger code.
