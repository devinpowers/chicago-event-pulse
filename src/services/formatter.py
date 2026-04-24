from datetime import date
from html import escape
from typing import List

from src.models.event import Event


class EmailMessage:
    """The finished email content before it is sent."""

    def __init__(self, subject: str, html: str) -> None:
        self.subject = subject
        self.html = html


class EventEmailFormatter:
    """Turns Event objects into the email subject and HTML body."""

    def build_message(
        self,
        events: List[Event],
        target_date: date,
        transit_summary: str | None = None,
        transit_pick_title: str | None = None,
        transit_pick_note: str | None = None,
    ) -> EmailMessage:
        subject = self.build_subject(target_date)
        html = self.build_html_email(
            events,
            target_date,
            transit_summary=transit_summary,
            transit_pick_title=transit_pick_title,
            transit_pick_note=transit_pick_note,
        )
        return EmailMessage(subject=subject, html=html)

    def build_subject(self, target_date: date) -> str:
        return f"Today's Chicago Events - {target_date.strftime('%B %-d, %Y')}"

    def build_html_email(
        self,
        events: List[Event],
        target_date: date,
        transit_summary: str | None = None,
        transit_pick_title: str | None = None,
        transit_pick_note: str | None = None,
    ) -> str:
        event_blocks = []

        for event in events:
            event_blocks.append(self._event_block(event))

        rows = "\n".join(event_blocks)
        if not rows:
            rows = self._empty_events_block()

        readable_date = escape(target_date.strftime("%B %-d, %Y"))
        event_count = len(events)
        earliest_time = escape(self._earliest_time(events))
        lowest_price = escape(self._lowest_price(events))
        source_label = escape(self._source_label(events))
        transit_block = self._transit_block(transit_summary, transit_pick_title, transit_pick_note)

        return f"""<!doctype html>
<html>
  <body style="margin:0; padding:0; background-color:#eef3f6; font-family:Arial, Helvetica, sans-serif; color:#18232b;">
    <div style="display:none; max-height:0; overflow:hidden; color:#eef3f6; font-size:1px; line-height:1px;">
      {event_count} Chicago events for today, sorted by time with quick venue and ticket notes.
    </div>
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="margin:0; padding:0; background-color:#eef3f6;">
      <tr>
        <td align="center" style="padding:24px 12px;">
          <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="width:100%; max-width:640px; background-color:#ffffff; border:1px solid #d7e0e5;">
            <tr>
              <td style="padding:0; background-color:#2a7f9e; font-size:1px; line-height:6px;">&nbsp;</td>
            </tr>
            <tr>
              <td style="padding:28px 28px 18px 28px;">
                <p style="margin:0 0 8px 0; color:#b3263a; font-size:12px; line-height:16px; font-weight:bold; letter-spacing:0; text-transform:uppercase;">
                  Chicago Daily Events
                </p>
                <h1 style="margin:0; color:#18232b; font-size:28px; line-height:34px; font-weight:bold;">
                  Your plans, sorted
                </h1>
                <p style="margin:10px 0 0 0; color:#53616a; font-size:15px; line-height:22px;">
                  {readable_date} &middot; {event_count} nearby picks &middot; Times shown in Central Time
                </p>
              </td>
            </tr>
            <tr>
              <td style="padding:0 28px 24px 28px;">
                <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="background-color:#f7fafb; border:1px solid #d7e0e5;">
                  <tr>
                    <td style="padding:16px 16px 14px 16px;">
                      <p style="margin:0 0 10px 0; color:#18232b; font-size:16px; line-height:23px; font-weight:bold;">
                        Today at a glance
                      </p>
                      <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0">
                        <tr>
                          <td valign="top" width="33.33%" style="padding:0 8px 0 0;">
                            <p style="margin:0; color:#53616a; font-size:12px; line-height:16px;">Soonest</p>
                            <p style="margin:2px 0 0 0; color:#18232b; font-size:14px; line-height:20px; font-weight:bold;">{earliest_time}</p>
                          </td>
                          <td valign="top" width="33.33%" style="padding:0 8px;">
                            <p style="margin:0; color:#53616a; font-size:12px; line-height:16px;">Lowest price</p>
                            <p style="margin:2px 0 0 0; color:#18232b; font-size:14px; line-height:20px; font-weight:bold;">{lowest_price}</p>
                          </td>
                          <td valign="top" width="33.33%" style="padding:0 0 0 8px;">
                            <p style="margin:0; color:#53616a; font-size:12px; line-height:16px;">Sources</p>
                            <p style="margin:2px 0 0 0; color:#18232b; font-size:14px; line-height:20px; font-weight:bold;">{source_label}</p>
                          </td>
                        </tr>
                      </table>
                    </td>
                  </tr>
                </table>
              </td>
            </tr>
            {transit_block}
            <tr>
              <td style="padding:0 28px 8px 28px;">
                <h2 style="margin:0; color:#18232b; font-size:18px; line-height:24px; font-weight:bold;">
                  Today's picks
                </h2>
              </td>
            </tr>
            {rows}
            <tr>
              <td style="padding:24px 28px 28px 28px;">
                <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="background-color:#f7fafb; border:1px solid #d7e0e5;">
                  <tr>
                    <td style="padding:16px;">
                      <p style="margin:0 0 8px 0; color:#18232b; font-size:15px; line-height:22px; font-weight:bold;">
                        Planning note
                      </p>
                      <p style="margin:0; color:#53616a; font-size:14px; line-height:21px;">
                        Check venue pages before heading out. Times, availability, and prices can change during the day.
                      </p>
                    </td>
                  </tr>
                </table>
                <p style="margin:18px 0 0 0; color:#6a777f; font-size:12px; line-height:18px;">
                  Source: {source_label} &middot; Sent by Azure Functions at 7:00 AM America/Chicago
                </p>
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>
  </body>
</html>"""

    def _event_block(self, event: Event) -> str:
        title = escape(event.title)
        venue = escape(event.venue or "Venue unavailable")
        category = escape(event.category or "Event")
        start_time = escape(event.start_time or "Time unavailable")
        price = escape(self._format_price(event))
        link = escape(event.url or "#")
        detail_line = escape(self._event_detail_line(event, price))
        transit_note = self._transit_note_block(event)

        return f"""
            <tr>
              <td style="padding:0 28px;">
                <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="border-top:1px solid #d7e0e5;">
                  <tr>
                    <td valign="top" width="82" style="padding:18px 14px 18px 0;">
                      <p style="margin:0; color:#b3263a; font-size:12px; line-height:16px; font-weight:bold;">{start_time}</p>
                      <p style="margin:4px 0 0 0; color:#53616a; font-size:12px; line-height:16px;">{category}</p>
                    </td>
                    <td valign="top" style="padding:18px 0;">
                      <h3 style="margin:0 0 6px 0; color:#18232b; font-size:18px; line-height:24px; font-weight:bold;">{title}</h3>
                      <p style="margin:0 0 12px 0; color:#53616a; font-size:14px; line-height:21px;">{detail_line}</p>
                      {transit_note}
                      <table role="presentation" cellspacing="0" cellpadding="0" border="0">
                        <tr>
                          <td bgcolor="#2a7f9e" style="padding:9px 14px;">
                            <a href="{link}" style="display:inline-block; color:#ffffff; font-size:14px; line-height:18px; font-weight:bold; text-decoration:none;">View details</a>
                          </td>
                        </tr>
                      </table>
                    </td>
                  </tr>
                </table>
              </td>
            </tr>"""

    def _format_price(self, event: Event) -> str:
        if event.price_min is None and event.price_max is None:
            return "Price unavailable"
        if event.price_min == event.price_max:
            return f"${event.price_min:g}"
        if event.price_min is not None and event.price_max is not None:
            return f"${event.price_min:g}-${event.price_max:g}"
        if event.price_min is not None:
            return f"From ${event.price_min:g}"
        return f"Up to ${event.price_max:g}"

    def _empty_events_block(self) -> str:
        return """
            <tr>
              <td style="padding:0 28px;">
                <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="border-top:1px solid #d7e0e5;">
                  <tr>
                    <td style="padding:18px 0;">
                      <p style="margin:0; color:#53616a; font-size:14px; line-height:21px;">
                        No events were found for Chicago today.
                      </p>
                    </td>
                  </tr>
                </table>
              </td>
            </tr>"""

    def _earliest_time(self, events: List[Event]) -> str:
        event_times = [event.start_time for event in events if event.start_time]
        if not event_times:
            return "Time unavailable"

        return sorted(event_times)[0]

    def _lowest_price(self, events: List[Event]) -> str:
        prices = [event.price_min for event in events if event.price_min is not None]
        if not prices:
            return "Price unavailable"

        return f"From ${min(prices):g}"

    def _source_label(self, events: List[Event]) -> str:
        sources = sorted({event.source for event in events if event.source})
        if not sources:
            return "Configured event APIs"

        return ", ".join(sources)

    def _event_detail_line(self, event: Event, price: str) -> str:
        details = []

        if event.venue:
            details.append(event.venue)
        if event.address:
            details.append(event.address)

        details.append(price)
        details.append(f"Source: {event.source}")
        return " | ".join(details)

    def _transit_block(
        self,
        transit_summary: str | None,
        transit_pick_title: str | None,
        transit_pick_note: str | None,
    ) -> str:
        if not transit_summary and not transit_pick_title:
            return ""

        summary_html = ""
        if transit_summary:
            summary_html = f"""
                      <p style="margin:0; color:#18232b; font-size:14px; line-height:21px;">{escape(transit_summary)}</p>
"""

        pick_html = ""
        if transit_pick_title and transit_pick_note:
            pick_html = f"""
                      <p style="margin:10px 0 0 0; color:#18232b; font-size:14px; line-height:21px;"><strong>Best easy ride:</strong> {escape(transit_pick_title)}<br />{escape(transit_pick_note)}</p>
"""

        return f"""
            <tr>
              <td style="padding:0 28px 24px 28px;">
                <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="background-color:#f7fafb; border:1px solid #d7e0e5;">
                  <tr>
                    <td style="padding:16px;">
                      <p style="margin:0 0 8px 0; color:#18232b; font-size:15px; line-height:22px; font-weight:bold;">
                        CTA Watch
                      </p>
                      {summary_html}{pick_html}
                    </td>
                  </tr>
                </table>
              </td>
            </tr>"""

    def _transit_note_block(self, event: Event) -> str:
        if not event.transit_note:
            return ""

        return f'<p style="margin:0 0 12px 0; color:#18232b; font-size:13px; line-height:20px;">{escape(event.transit_note)}</p>'


def build_subject(target_date: date) -> str:
    """Compatibility helper for older tests or scripts."""
    return EventEmailFormatter().build_subject(target_date)


def build_html_email(
    events: List[Event],
    target_date: date,
    transit_summary: str | None = None,
    transit_pick_title: str | None = None,
    transit_pick_note: str | None = None,
) -> str:
    """Compatibility helper for older tests or scripts."""
    return EventEmailFormatter().build_html_email(
        events,
        target_date,
        transit_summary=transit_summary,
        transit_pick_title=transit_pick_title,
        transit_pick_note=transit_pick_note,
    )
