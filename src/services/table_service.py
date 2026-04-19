from datetime import date
from decimal import Decimal
from typing import List, Optional

from src.models.event import Event


class TableStorageService:
    def __init__(self, account_name: str, connection_string: Optional[str] = None) -> None:
        if connection_string and not connection_string.startswith("@Microsoft.KeyVault"):
            from azure.data.tables import TableServiceClient

            self.client = TableServiceClient.from_connection_string(connection_string)
        else:
            raise RuntimeError(f"Missing storage connection string for account: {account_name}")

    def upsert_digest(self, target_date: date, digest: dict) -> None:
        table = self.client.get_table_client("Digests")
        table.upsert_entity(
            {
                "PartitionKey": "Chicago",
                "RowKey": target_date.isoformat(),
                **_table_safe(digest),
            }
        )

    def upsert_events(self, target_date: date, events: List[Event]) -> None:
        table = self.client.get_table_client("Events")
        for index, event in enumerate(events):
            event_dict = _table_safe(event.to_dict())
            row_key = event.source_event_id or event.event_id or f"{index:03d}"
            table.upsert_entity(
                {
                    "PartitionKey": target_date.isoformat(),
                    "RowKey": _clean_row_key(row_key),
                    **event_dict,
                }
            )

    def upsert_email_log(self, target_date: date, send_result: dict) -> None:
        table = self.client.get_table_client("EmailLogs")
        row_key = send_result.get("provider_message_id") or send_result.get("sent_at") or "latest"
        table.upsert_entity(
            {
                "PartitionKey": target_date.isoformat(),
                "RowKey": _clean_row_key(row_key),
                **_table_safe(send_result),
            }
        )


def _table_safe(payload: dict) -> dict:
    safe = {}
    for key, value in payload.items():
        if value is None:
            continue
        if isinstance(value, Decimal):
            safe[key] = float(value)
        elif isinstance(value, (str, int, float, bool)):
            safe[key] = value
        else:
            safe[key] = str(value)
    return safe


def _clean_row_key(value: str) -> str:
    return value.replace("/", "_").replace("\\", "_").replace("#", "_").replace("?", "_")
