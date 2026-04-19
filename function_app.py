import json
import logging
from datetime import date, datetime
from zoneinfo import ZoneInfo

import azure.functions as func

from src.config import AppConfig
from src.functions.daily_events_timer import run_daily_events_digest

app = func.FunctionApp()


@app.timer_trigger(
    schedule="0 0 7 * * *",
    arg_name="timer",
    run_on_startup=False,
    use_monitor=True,
)
def daily_events_timer(timer: func.TimerRequest) -> None:
    """Run daily at 7 AM America/Chicago."""
    now = datetime.now(ZoneInfo("America/Chicago"))
    logging.info("Starting Chicago Event Pulse run for %s.", now.date().isoformat())

    config = AppConfig.from_env()
    run_daily_events_digest(config=config, target_date=now.date())


@app.route(route="run-digest", methods=["POST"], auth_level=func.AuthLevel.FUNCTION)
def run_digest(req: func.HttpRequest) -> func.HttpResponse:
    """Run the daily digest on demand for MVP testing."""
    try:
        target_date = _target_date_from_request(req)
        config = AppConfig.from_env()
        digest = run_daily_events_digest(config=config, target_date=target_date)
        return _json_response({"ok": True, "digest": digest})
    except Exception as exc:
        logging.exception("Manual digest run failed.")
        return _json_response({"ok": False, "error": str(exc)}, status_code=500)


def _target_date_from_request(req: func.HttpRequest) -> date:
    raw_date = req.params.get("date")
    if not raw_date:
        raw_date = datetime.now(ZoneInfo("America/Chicago")).date().isoformat()

    return date.fromisoformat(raw_date)


def _json_response(payload: dict, status_code: int = 200) -> func.HttpResponse:
    return func.HttpResponse(
        body=json.dumps(payload, indent=2),
        status_code=status_code,
        mimetype="application/json",
    )
