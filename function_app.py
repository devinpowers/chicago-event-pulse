import logging
from datetime import datetime
from zoneinfo import ZoneInfo

import azure.functions as func

from src.config import AppConfig
from src.functions.daily_events_timer import run_daily_events_digest

app = func.FunctionApp()


@app.timer_trigger(
    schedule="0 0 12 * * *",
    arg_name="timer",
    run_on_startup=False,
    use_monitor=True,
)
def daily_events_timer(timer: func.TimerRequest) -> None:
    """Run daily at 7 AM Central Time when Azure uses UTC."""
    now = datetime.now(ZoneInfo("America/Chicago"))
    logging.info("Starting Chicago Event Pulse run for %s.", now.date().isoformat())

    config = AppConfig.from_env()
    run_daily_events_digest(config=config, target_date=now.date())

