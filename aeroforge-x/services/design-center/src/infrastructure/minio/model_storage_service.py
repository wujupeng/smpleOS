from __future__ import annotations

import hashlib
from typing import Any

from aeroforge_db.minio import upload_file, download_file, get_presigned_url, ensure_bucket


class ModelStorageService:
    BUCKET_NAME = "aeroforge-models"

    def __init__(self) -> None:
        ensure_bucket(self.BUCKET_NAME)

    async def store_model(self, spec_id: str, model_data: bytes, content_type: str = "application/json") -> dict[str, Any]:
        object_key = f"models/{spec_id}/model.json"
        checksum = hashlib.sha256(model_data).hexdigest()
        upload_file(
            bucket_name=self.BUCKET_NAME,
            object_key=object_key,
            data=model_data,
            content_type=content_type,
        )
        return {
            "bucket": self.BUCKET_NAME,
            "object_key": object_key,
            "size_bytes": len(model_data),
            "sha256": checksum,
        }

    async def retrieve_model(self, spec_id: str) -> bytes | None:
        try:
            object_key = f"models/{spec_id}/model.json"
            return download_file(self.BUCKET_NAME, object_key)
        except Exception:
            return None

    async def get_download_url(self, spec_id: str, expires: int = 3600) -> str:
        object_key = f"models/{spec_id}/model.json"
        return get_presigned_url(self.BUCKET_NAME, object_key, expires=expires)

    async def store_step_model(self, spec_id: str, step_data: bytes) -> dict[str, Any]:
        object_key = f"models/{spec_id}/aircraft.step"
        checksum = hashlib.sha256(step_data).hexdigest()
        upload_file(
            bucket_name=self.BUCKET_NAME,
            object_key=object_key,
            data=step_data,
            content_type="application/step",
        )
        return {
            "bucket": self.BUCKET_NAME,
            "object_key": object_key,
            "size_bytes": len(step_data),
            "sha256": checksum,
        }