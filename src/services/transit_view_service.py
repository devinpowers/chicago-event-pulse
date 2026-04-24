import os
from dataclasses import replace
from datetime import date

from azure.core.exceptions import ResourceNotFoundError

from src.models.event import Event
from src.services.cta_service import CtaTransitService
from src.services.event_sources.seatgeek import SeatGeekEventSource
from src.services.event_sources.ticketmaster import normalize_ticketmaster_events
from src.services.storage_service import StorageService


class TransitViewService:
    def __init__(self, storage: StorageService, transit_service: CtaTransitService) -> None:
        self.storage = storage
        self.transit_service = transit_service

    @classmethod
    def from_env(cls) -> "TransitViewService":
        account_name = os.getenv("STORAGE_ACCOUNT_NAME")
        connection_string = os.getenv("AzureWebJobsStorage")
        if not account_name or not connection_string:
            raise RuntimeError("Transit view requires storage configuration.")

        return cls(
            storage=StorageService(account_name=account_name, connection_string=connection_string),
            transit_service=CtaTransitService(),
        )

    def build_view_data(self, target_date: date) -> dict:
        try:
            events_payload = self.storage.download_json("processed-events", target_date, "events.json")
        except ResourceNotFoundError:
            events_payload = []

        events = [Event.from_dict(item) for item in events_payload]
        events = self._restore_coordinates(target_date, events)
        enriched = self.transit_service.enrich_events(events).events
        map_data = self.transit_service.build_map_data(enriched)

        return {
            "date": target_date.isoformat(),
            "generated_at": map_data.generated_at,
            "summary": map_data.summary,
            "route_statuses": map_data.route_statuses,
            "events": map_data.events,
        }

    def _restore_coordinates(self, target_date: date, events: list[Event]) -> list[Event]:
        if not events or all(event.latitude is not None and event.longitude is not None for event in events):
            return events

        supplemental: dict[str, Event] = {}
        supplemental.update(self._normalized_raw_events(target_date, "ticketmaster.json", normalize_ticketmaster_events))
        supplemental.update(
            self._normalized_raw_events(
                target_date,
                "seatgeek.json",
                lambda payload: SeatGeekEventSource(client_id="").normalize_events(payload),
            )
        )

        restored_events = []
        for event in events:
            matched = supplemental.get(self._event_lookup_key(event))
            if matched and event.latitude is None and matched.latitude is not None:
                restored_events.append(
                    replace(
                        event,
                        latitude=matched.latitude,
                        longitude=matched.longitude,
                    )
                )
            else:
                restored_events.append(event)

        return restored_events

    def _normalized_raw_events(self, target_date: date, file_name: str, normalizer) -> dict[str, Event]:
        try:
            payload = self.storage.download_json("raw-events", target_date, file_name)
        except ResourceNotFoundError:
            return {}

        lookup = {}
        for event in normalizer(payload):
            lookup[self._event_lookup_key(event)] = event
        return lookup

    def _event_lookup_key(self, event: Event) -> str:
        if event.source_event_id:
            return f"{event.source}:{event.source_event_id}"
        if event.url:
            return f"{event.source}:{event.url}"
        return f"{event.source}:{event.title}:{event.venue}"


def build_transit_view_html(target_date: date) -> str:
    readable_date = target_date.strftime("%B %-d, %Y")
    date_value = target_date.isoformat()
    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Chicago CTA Transit View</title>
    <link
      rel="stylesheet"
      href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"
      integrity="sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY="
      crossorigin=""
    />
    <style>
      :root {{
        color-scheme: dark;
        --ink: #f2f6f8;
        --muted: #a9b7bf;
        --line: #25404c;
        --bg: #071116;
        --panel: #0c1b23;
        --panel-strong: #102631;
        --accent: #22c7a7;
        --accent-soft: rgba(34, 199, 167, 0.15);
        --warn: #f4b942;
        --alert: #ff6b6b;
        --shadow: rgba(0, 0, 0, 0.28);
      }}

      * {{ box-sizing: border-box; }}

      body {{
        margin: 0;
        font-family: Arial, Helvetica, sans-serif;
        color: var(--ink);
        background: var(--bg);
      }}

      .shell {{
        min-height: 100vh;
        display: grid;
        grid-template-columns: minmax(320px, 390px) minmax(0, 1fr);
      }}

      .sidebar {{
        background: var(--panel);
        border-right: 1px solid var(--line);
        display: flex;
        flex-direction: column;
        min-height: 100vh;
        position: relative;
        z-index: 2;
      }}

      .panel {{
        padding: 22px 20px 18px 20px;
      }}

      h1 {{
        margin: 0;
        font-size: 31px;
        line-height: 36px;
      }}

      .eyebrow {{
        margin: 0 0 8px 0;
        color: var(--accent);
        font-size: 12px;
        line-height: 16px;
        text-transform: uppercase;
        font-weight: bold;
      }}

      .meta, .summary {{
        margin: 10px 0 0 0;
        color: var(--muted);
        font-size: 14px;
        line-height: 21px;
      }}

      .lede {{
        margin: 14px 0 0 0;
        color: var(--ink);
        font-size: 15px;
        line-height: 23px;
      }}

      .summary-band {{
        margin-top: 16px;
        padding: 14px;
        border: 1px solid var(--line);
        border-radius: 8px;
        background: linear-gradient(180deg, rgba(20, 44, 55, 0.95), rgba(12, 27, 35, 0.95));
        box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.03);
      }}

      .metric-row {{
        margin-top: 14px;
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 8px;
      }}

      .metric {{
        border: 1px solid var(--line);
        border-radius: 8px;
        padding: 10px;
        background: rgba(255, 255, 255, 0.02);
      }}

      .metric-label {{
        margin: 0;
        color: var(--muted);
        font-size: 11px;
        line-height: 14px;
        text-transform: uppercase;
        font-weight: bold;
      }}

      .metric-value {{
        margin: 6px 0 0 0;
        font-size: 16px;
        line-height: 20px;
        font-weight: bold;
      }}

      .toolbar {{
        padding: 0 20px 18px 20px;
        display: flex;
        gap: 10px;
        align-items: end;
        flex-wrap: wrap;
      }}

      .toolbar-group {{
        display: flex;
        flex-direction: column;
        gap: 6px;
      }}

      .toolbar-label {{
        color: var(--muted);
        font-size: 12px;
        line-height: 16px;
      }}

      .toolbar input {{
        border: 1px solid var(--line);
        border-radius: 8px;
        padding: 10px 12px;
        font-size: 14px;
        background: var(--panel-strong);
        color: var(--ink);
      }}

      .toolbar button {{
        border: 1px solid var(--accent);
        background: var(--accent);
        color: #042a23;
        border-radius: 8px;
        padding: 10px 14px;
        font-size: 14px;
        font-weight: bold;
        cursor: pointer;
      }}

      .chip-row {{
        padding: 0 20px 18px 20px;
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
      }}

      .route-strip {{
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
      }}

      .route-pill,
      .filter-pill {{
        border: 1px solid var(--line);
        border-radius: 8px;
        padding: 8px 10px;
        background: rgba(255, 255, 255, 0.03);
        font-size: 12px;
        line-height: 16px;
        cursor: pointer;
        color: var(--ink);
      }}

      .route-pill[data-active="true"],
      .filter-pill[data-active="true"] {{
        border-color: var(--accent);
        background: var(--accent-soft);
      }}

      .list {{
        overflow: auto;
        padding: 0 20px 24px 20px;
      }}

      .event-item {{
        border-top: 1px solid var(--line);
        padding: 16px 0;
        cursor: pointer;
      }}

      .event-item:first-child {{
        border-top: 0;
      }}

      .event-item[data-selected="true"] {{
        background: linear-gradient(90deg, rgba(34, 199, 167, 0.12), rgba(34, 199, 167, 0));
        margin: 0 -20px;
        padding: 16px 20px;
      }}

      .event-title {{
        margin: 0 0 6px 0;
        font-size: 18px;
        line-height: 24px;
      }}

      .event-kicker {{
        margin: 0 0 8px 0;
        color: var(--accent);
        font-size: 11px;
        line-height: 14px;
        text-transform: uppercase;
        font-weight: bold;
      }}

      .event-detail, .station-detail {{
        margin: 0;
        color: var(--muted);
        font-size: 14px;
        line-height: 21px;
      }}

      .event-note {{
        margin: 8px 0 0 0;
        font-size: 13px;
        line-height: 19px;
      }}

      .event-link {{
        display: inline-block;
        margin-top: 10px;
        color: var(--accent);
        text-decoration: none;
        font-weight: bold;
      }}

      .map-wrap {{
        min-height: 100vh;
        position: relative;
        background: radial-gradient(circle at top, rgba(34, 199, 167, 0.12), transparent 28%), #071116;
      }}

      .map-hero {{
        position: absolute;
        top: 18px;
        left: 18px;
        right: 18px;
        z-index: 600;
        display: grid;
        grid-template-columns: minmax(0, 1fr) minmax(280px, 360px);
        gap: 14px;
        pointer-events: none;
      }}

      .hero-card,
      .spotlight {{
        pointer-events: auto;
        border: 1px solid rgba(82, 111, 123, 0.75);
        border-radius: 8px;
        background: rgba(7, 17, 22, 0.84);
        backdrop-filter: blur(10px);
        box-shadow: 0 14px 36px var(--shadow);
      }}

      .hero-card {{
        padding: 18px;
        align-self: start;
      }}

      .hero-card h2,
      .spotlight h2 {{
        margin: 0;
        font-size: 24px;
        line-height: 28px;
      }}

      .hero-card p,
      .spotlight p {{
        margin: 10px 0 0 0;
        font-size: 14px;
        line-height: 21px;
        color: var(--muted);
      }}

      .hero-tags {{
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        margin-top: 14px;
      }}

      .hero-tag {{
        border-radius: 8px;
        border: 1px solid var(--line);
        padding: 7px 9px;
        font-size: 12px;
        line-height: 16px;
        background: rgba(255, 255, 255, 0.03);
      }}

      .spotlight {{
        padding: 18px;
        align-self: start;
      }}

      #map {{
        width: 100%;
        height: 100vh;
        min-height: 70vh;
      }}

      .leaflet-popup-content {{
        margin: 12px 14px;
      }}

      .popup-title {{
        margin: 0 0 6px 0;
        font-size: 16px;
        line-height: 20px;
      }}

      .popup-line {{
        margin: 0;
        font-size: 13px;
        line-height: 18px;
        color: var(--muted);
      }}

      .legend {{
        position: absolute;
        right: 18px;
        bottom: 18px;
        z-index: 600;
        border: 1px solid rgba(82, 111, 123, 0.75);
        border-radius: 8px;
        background: rgba(7, 17, 22, 0.84);
        backdrop-filter: blur(10px);
        padding: 14px;
        width: min(300px, calc(100vw - 36px));
        box-shadow: 0 14px 36px var(--shadow);
      }}

      .legend-title {{
        margin: 0 0 8px 0;
        font-size: 13px;
        line-height: 17px;
        color: var(--muted);
        text-transform: uppercase;
        font-weight: bold;
      }}

      .legend-row {{
        display: flex;
        align-items: center;
        gap: 8px;
        margin-top: 8px;
        font-size: 13px;
        line-height: 18px;
        color: var(--muted);
      }}

      .legend-dot {{
        width: 12px;
        height: 12px;
        border-radius: 999px;
        flex: 0 0 auto;
      }}

      .empty {{
        color: var(--muted);
        padding: 20px;
      }}

      @media (max-width: 900px) {{
        .shell {{
          grid-template-columns: 1fr;
          grid-template-rows: auto minmax(72vh, 1fr);
        }}

        .sidebar {{
          min-height: auto;
          border-right: 0;
          border-bottom: 1px solid var(--line);
        }}

        .metric-row {{
          grid-template-columns: 1fr;
        }}

        .map-hero {{
          grid-template-columns: 1fr;
          top: auto;
          left: 12px;
          right: 12px;
          bottom: 12px;
        }}

        .hero-card {{
          display: none;
        }}

        #map {{
          height: 72vh;
        }}
      }}
    </style>
  </head>
  <body>
    <div class="shell">
      <aside class="sidebar">
        <div class="panel">
          <p class="eyebrow">Chicago transit view</p>
          <h1>Pick a night out by how the city moves.</h1>
          <p class="meta">{readable_date}</p>
          <p class="lede">A live CTA night map that pairs real events with the stations, lines, and friction around them.</p>
          <div class="summary-band">
            <p class="summary" id="summary">Loading CTA status...</p>
            <div class="metric-row">
              <div class="metric">
                <p class="metric-label">Visible plans</p>
                <p class="metric-value" id="metric-events">0</p>
              </div>
              <div class="metric">
                <p class="metric-label">Easy rides</p>
                <p class="metric-value" id="metric-easy">0</p>
              </div>
              <div class="metric">
                <p class="metric-label">Lines in play</p>
                <p class="metric-value" id="metric-lines">0</p>
              </div>
            </div>
          </div>
        </div>
        <div class="toolbar">
          <div class="toolbar-group">
            <label class="toolbar-label" for="date-input">Date</label>
            <input id="date-input" type="date" value="{date_value}" />
          </div>
          <button id="load-button" type="button">Load</button>
        </div>
        <div class="chip-row">
          <div class="route-strip" id="route-strip"></div>
          <div class="route-strip" id="filter-strip"></div>
        </div>
        <div class="list" id="event-list">
          <p class="empty">Loading events...</p>
        </div>
      </aside>
      <main class="map-wrap">
        <div class="map-hero">
          <section class="hero-card">
            <p class="eyebrow" style="margin:0;">Tonight on the rails</p>
            <h2>See the plans, not just the lines.</h2>
            <p>Events glow brighter than the network. Click a plan to trace the walk from its nearest station and get the live line status around it.</p>
            <div class="hero-tags">
              <span class="hero-tag">Easy ride picks</span>
              <span class="hero-tag">Station-to-venue links</span>
              <span class="hero-tag">Live CTA watch</span>
            </div>
          </section>
          <section class="spotlight" id="spotlight">
            <p class="eyebrow" style="margin:0;">Spotlight</p>
            <h2>Loading tonight's best route...</h2>
            <p>Pick an event from the list to focus the map.</p>
          </section>
        </div>
        <div id="map" aria-label="Chicago CTA transit map"></div>
        <aside class="legend">
          <p class="legend-title">How to read the map</p>
          <div class="legend-row"><span class="legend-dot" style="background:#22c7a7;"></span> Event venue</div>
          <div class="legend-row"><span class="legend-dot" style="background:#f4b942;"></span> Connected station</div>
          <div class="legend-row"><span class="legend-dot" style="background:#ff6b6b;"></span> Delay-heavy route</div>
        </aside>
      </main>
    </div>

    <script
      src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"
      integrity="sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo="
      crossorigin=""
    ></script>
    <script>
      const chicagoCenter = [41.8781, -87.6298];
      const map = L.map('map', {{ zoomControl: true }}).setView(chicagoCenter, 11);
      L.tileLayer('https://{{s}}.basemaps.cartocdn.com/dark_all/{{z}}/{{x}}/{{y}}{{r}}.png', {{
        maxZoom: 19,
        subdomains: 'abcd',
        attribution: '&copy; OpenStreetMap contributors &copy; CARTO'
      }}).addTo(map);

      const eventLayer = L.layerGroup().addTo(map);
      const stationLayer = L.layerGroup().addTo(map);
      const routeStrip = document.getElementById('route-strip');
      const filterStrip = document.getElementById('filter-strip');
      const summary = document.getElementById('summary');
      const eventList = document.getElementById('event-list');
      const dateInput = document.getElementById('date-input');
      const loadButton = document.getElementById('load-button');
      const spotlight = document.getElementById('spotlight');
      const metricEvents = document.getElementById('metric-events');
      const metricEasy = document.getElementById('metric-easy');
      const metricLines = document.getElementById('metric-lines');

      let activeLine = '';
      let activeFilter = 'all';
      let allEvents = [];
      let selectedEventTitle = '';
      let currentRouteStatuses = [];

      function statusTone(status) {{
        if (status === 'Normal Service') return '#0f766e';
        if (status.includes('Delay') || status.includes('Disruption') || status.includes('Suspended')) return '#ff6b6b';
        return '#f4b942';
      }}

      function renderRouteStrip(routeStatuses) {{
        routeStrip.innerHTML = '';
        const allButton = buildPill('All lines', activeLine === '', 'route-pill', () => {{
          activeLine = '';
          renderRouteStrip(routeStatuses);
          renderEvents();
        }});
        routeStrip.appendChild(allButton);

        routeStatuses.forEach((route) => {{
          const button = buildPill(`${{route.line_name}} - ${{route.status}}`, activeLine === route.line_name, 'route-pill', () => {{
            activeLine = activeLine === route.line_name ? '' : route.line_name;
            renderRouteStrip(routeStatuses);
            renderEvents();
          }});
          button.style.borderColor = statusTone(route.status);
          routeStrip.appendChild(button);
        }});
      }}

      function renderFilterStrip() {{
        filterStrip.innerHTML = '';
        const filters = [
          ['all', 'All plans'],
          ['easy', 'Easy ride'],
          ['music', 'Music'],
          ['theater', 'Theater'],
          ['cheap', 'Lower cost'],
        ];

        filters.forEach(([value, label]) => {{
          filterStrip.appendChild(buildPill(label, activeFilter === value, 'filter-pill', () => {{
            activeFilter = value;
            renderFilterStrip();
            renderEvents();
          }}));
        }});
      }}

      function buildPill(label, active, className, onClick) {{
        const button = document.createElement('button');
        button.className = className;
        button.dataset.active = active ? 'true' : 'false';
        button.type = 'button';
        button.textContent = label;
        button.onclick = onClick;
        return button;
      }}

      function filteredEvents() {{
        return allEvents.filter((event) => {{
          if (activeLine) {{
            const station = event.station;
            if (!station || !station.lines.includes(activeLine)) {{
              return false;
            }}
          }}

          if (activeFilter === 'easy') {{
            return (event.transit_score || 0) >= 80;
          }}
          if (activeFilter === 'music') {{
            return (event.category || '').toLowerCase().includes('music');
          }}
          if (activeFilter === 'theater') {{
            const category = (event.category || '').toLowerCase();
            return category.includes('arts') || category.includes('theatre') || category.includes('theater');
          }}
          if (activeFilter === 'cheap') {{
            return event.price_min !== null && event.price_min !== undefined && event.price_min <= 30;
          }}

          return true;
        }});
      }}

      function eventTone(event) {{
        const score = event.transit_score || 0;
        if (score >= 85) return '#22c7a7';
        if (score >= 60) return '#f4b942';
        return '#ff6b6b';
      }}

      function renderSpotlight(event) {{
        if (!event) {{
          spotlight.innerHTML = `
            <p class="eyebrow" style="margin:0;">Spotlight</p>
            <h2>Pick a plan from the left.</h2>
            <p>The map will snap to its nearest station and highlight the live CTA context around it.</p>
          `;
          return;
        }}

        const stationName = event.station ? event.station.name : 'No nearby rail stop';
        const stationLines = event.station ? event.station.lines.join(', ') : 'Transit fallback needed';
        const priceText = event.price_min !== null && event.price_min !== undefined
          ? `From $${{Number(event.price_min).toFixed(event.price_min % 1 === 0 ? 0 : 2)}}`
          : 'Price unavailable';
        const alerts = event.station && event.station.alerts.length
          ? `<p style="margin-top:10px; color:var(--alert);">${{event.station.alerts.map((alert) => alert.headline).join(' | ')}}</p>`
          : '';

        spotlight.innerHTML = `
          <p class="eyebrow" style="margin:0;">Spotlight</p>
          <h2>${{event.title}}</h2>
          <p>${{event.start_time || 'Time unavailable'}} | ${{event.venue || 'Venue unavailable'}} | ${{priceText}}</p>
          <p>${{event.transit_note || 'Transit note unavailable.'}}</p>
          <p>${{stationName}} | ${{stationLines}}</p>
          ${{alerts}}
        `;
      }}

      function updateMetrics(events) {{
        const easyCount = events.filter((event) => (event.transit_score || 0) >= 80).length;
        const lines = new Set();
        events.forEach((event) => {{
          const station = event.station;
          if (station) {{
            station.lines.forEach((line) => lines.add(line));
          }}
        }});
        metricEvents.textContent = String(events.length);
        metricEasy.textContent = String(easyCount);
        metricLines.textContent = String(lines.size);
      }}

      function renderEvents() {{
        const events = filteredEvents();
        eventList.innerHTML = '';
        eventLayer.clearLayers();
        stationLayer.clearLayers();
        updateMetrics(events);

        if (!events.length) {{
          eventList.innerHTML = '<p class="empty">No events match this filter yet.</p>';
          renderSpotlight(null);
          return;
        }}

        if (!selectedEventTitle || !events.find((event) => event.title === selectedEventTitle)) {{
          selectedEventTitle = events[0].title;
        }}

        const bounds = [];

        events.forEach((event) => {{
          const item = document.createElement('section');
          item.className = 'event-item';
          item.dataset.selected = event.title === selectedEventTitle ? 'true' : 'false';
          item.onclick = () => {{
            selectedEventTitle = event.title;
            renderEvents();
          }};

          const stationLines = event.station ? event.station.lines.join(', ') : 'No nearby rail stop';
          const walkText = event.station && event.station.walk_minutes ? `${{event.station.walk_minutes}} min walk` : '';
          const alerts = event.station ? event.station.alerts.map((alert) => alert.headline).join(' | ') : '';
          const kicker = (event.transit_score || 0) >= 85 ? 'Easy ride' : (event.transit_score || 0) >= 60 ? 'Worth the trip' : 'Watch transit';
          const priceText = event.price_min !== null && event.price_min !== undefined
            ? `$${{Number(event.price_min).toFixed(event.price_min % 1 === 0 ? 0 : 2)}}${{event.price_max && event.price_max !== event.price_min ? `-$${{Number(event.price_max).toFixed(event.price_max % 1 === 0 ? 0 : 2)}}` : ''}}`
            : 'Price unavailable';

          item.innerHTML = `
            <p class="event-kicker">${{kicker}}</p>
            <h2 class="event-title">${{event.title}}</h2>
            <p class="event-detail">${{event.start_time || 'Time unavailable'}} | ${{event.venue || 'Venue unavailable'}} | ${{priceText}}</p>
            <p class="station-detail">${{stationLines}}${{walkText ? ' | ' + walkText : ''}}</p>
            <p class="event-note">${{event.transit_note || 'Transit note unavailable.'}}</p>
            ${{alerts ? `<p class="event-note" style="color:#b3263a;">${{alerts}}</p>` : ''}}
            ${{event.url ? `<a class="event-link" href="${{event.url}}" target="_blank" rel="noreferrer">View details</a>` : ''}}
          `;
          eventList.appendChild(item);

          if (event.coordinates) {{
            const eventLatLng = [event.coordinates.latitude, event.coordinates.longitude];
            bounds.push(eventLatLng);
            const popup = `
              <h3 class="popup-title">${{event.title}}</h3>
              <p class="popup-line">${{event.venue || 'Venue unavailable'}}</p>
              <p class="popup-line">${{event.transit_note || ''}}</p>
            `;
            L.circleMarker(eventLatLng, {{
              radius: event.title === selectedEventTitle ? 10 : 7,
              color: eventTone(event),
              weight: 2,
              fillColor: eventTone(event),
              fillOpacity: 0.85,
            }}).bindPopup(popup).addTo(eventLayer)
              .on('click', () => {{
                selectedEventTitle = event.title;
                renderEvents();
              }});
          }}

          if (event.station && event.station.coordinates) {{
            const stationLatLng = [event.station.coordinates.latitude, event.station.coordinates.longitude];
            bounds.push(stationLatLng);
            const stationPopup = `
              <h3 class="popup-title">${{event.station.name}}</h3>
              <p class="popup-line">${{event.station.lines.join(', ')}}</p>
              <p class="popup-line">${{event.station.line_statuses.map((line) => `${{line.line}}: ${{line.status}}`).join(' | ')}}</p>
            `;
            L.circleMarker(stationLatLng, {{
              radius: event.title === selectedEventTitle ? 8 : 6,
              color: '#f4b942',
              weight: 2,
              fillColor: '#f4b942',
              fillOpacity: 0.92,
            }}).bindPopup(stationPopup).addTo(stationLayer);

            if (event.coordinates) {{
              L.polyline(
                [
                  [event.coordinates.latitude, event.coordinates.longitude],
                  stationLatLng
                ],
                {{
                  color: eventTone(event),
                  weight: event.title === selectedEventTitle ? 4 : 2,
                  opacity: event.title === selectedEventTitle ? 0.95 : 0.52,
                  dashArray: event.title === selectedEventTitle ? '1 0' : '5 6'
                }}
              ).addTo(stationLayer);
            }}
          }}
        }});

        renderSpotlight(events.find((event) => event.title === selectedEventTitle) || events[0]);

        if (bounds.length) {{
          map.fitBounds(bounds, {{ padding: [28, 28] }});
        }} else {{
          map.setView(chicagoCenter, 11);
        }}
      }}

      async function loadData() {{
        const dateValue = dateInput.value;
        summary.textContent = 'Loading CTA status...';
        eventList.innerHTML = '<p class="empty">Loading events...</p>';

        const response = await fetch(`/api/transit-view-data?date=${{encodeURIComponent(dateValue)}}`);
        const payload = await response.json();

        if (!payload.ok) {{
          summary.textContent = payload.error || 'Transit data is unavailable right now.';
          eventList.innerHTML = '<p class="empty">Nothing to show yet.</p>';
          routeStrip.innerHTML = '';
          filterStrip.innerHTML = '';
          eventLayer.clearLayers();
          stationLayer.clearLayers();
          renderSpotlight(null);
          return;
        }}

        summary.textContent = payload.data.summary;
        allEvents = payload.data.events || [];
        currentRouteStatuses = payload.data.route_statuses || [];
        activeLine = '';
        activeFilter = 'all';
        selectedEventTitle = '';
        renderRouteStrip(payload.data.route_statuses || []);
        renderFilterStrip();
        renderEvents();
      }}

      loadButton.addEventListener('click', loadData);
      dateInput.addEventListener('change', loadData);
      loadData();
    </script>
  </body>
</html>"""
