from datetime import date

from src.config import AppConfig
from src.services.digest_service import DailyDigestService


def run_daily_events_digest(config: AppConfig, target_date: date) -> dict:
    digest_service = DailyDigestService.from_config(config)
    return digest_service.run(target_date)
