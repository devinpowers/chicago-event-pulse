from datetime import date
from html import escape

from src.models.event import Event


def build_subject(target_date: date) -> str:
    return f"Today's Chicago Events - {target_date.strftime('%B %-d, %Y')}"


def build_html_email(events: list[Event], target_date: date) -> str:
    rows = "\n".join(_event_block(event) for event in events)
    if not rows:
        rows = "<p>No Ticketmaster events were found for Chicago today.</p>"

    return f"""<!doctype html>
<html>
  <body style="font-family: Arial, sans-serif; line-height: 1.5; color: #222;">
    <h1>Chicago Events for {escape(target_date.strftime('%B %-d, %Y'))}</h1>
    <p>Here are today's top events around Chicago.</p>
    {rows}
    <hr>
    <p style="font-size: 12px; color: #666;">Source: Ticketmaster Discovery API</p>
  </body>
</html>"""


def _event_block(event: Event) -> str:
    title = escape(event.title)
    venue = escape(event.venue or "Venue unavailable")
    category = escape(event.category or "Event")
    start_time = escape(event.start_time or "Time unavailable")
    price = escape(_format_price(event))
    link = escape(event.url or "#")

    return f"""
    <div style="margin-bottom: 20px;">
      <h2 style="margin-bottom: 4px;">{title}</h2>
      <p style="margin: 0;">{venue}</p>
      <p style="margin: 0;">{start_time} | {category} | {price}</p>
      <p style="margin: 0;"><a href="{link}">View event</a></p>
    </div>"""


def _format_price(event: Event) -> str:
    if event.price_min is None and event.price_max is None:
        return "Price unavailable"
    if event.price_min == event.price_max:
        return f"${event.price_min:g}"
    if event.price_min is not None and event.price_max is not None:
        return f"${event.price_min:g}-${event.price_max:g}"
    if event.price_min is not None:
        return f"From ${event.price_min:g}"
    return f"Up to ${event.price_max:g}"

