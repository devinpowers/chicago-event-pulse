import json
from datetime import date
from typing import Optional


class StorageService:
    def __init__(self, account_name: str, connection_string: Optional[str] = None) -> None:
        if connection_string and not connection_string.startswith("@Microsoft.KeyVault"):
            from azure.storage.blob import BlobServiceClient

            self.client = BlobServiceClient.from_connection_string(connection_string)
        else:
            raise RuntimeError(f"Missing storage connection string for account: {account_name}")

    def upload_json(self, container_name: str, target_date: date, file_name: str, payload: object) -> None:
        blob_name = f"{target_date:%Y/%m/%d}/{file_name}"
        blob_client = self.client.get_blob_client(container=container_name, blob=blob_name)
        data = json.dumps(payload, indent=2, default=str)
        blob_client.upload_blob(data, overwrite=True, content_type="application/json")

    def download_json(self, container_name: str, target_date: date, file_name: str) -> object:
        blob_name = f"{target_date:%Y/%m/%d}/{file_name}"
        blob_client = self.client.get_blob_client(container=container_name, blob=blob_name)
        data = blob_client.download_blob().readall()
        return json.loads(data)
