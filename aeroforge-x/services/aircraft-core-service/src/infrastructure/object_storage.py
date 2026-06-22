from __future__ import annotations

import io
import os
import uuid
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

ALLOWED_CONTENT_TYPES = frozenset({
    "application/pdf",
    "image/png",
    "image/jpeg",
    "image/tiff",
    "application/dxf",
    "application/step",
    "application/json",
    "text/csv",
    "application/zip",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.ms-excel",
})

PREDEFINED_BUCKETS = frozenset({
    "aeroforge-cert-evidence",
    "aeroforge-dataset-artifacts",
    "aeroforge-mdo-results",
    "aeroforge-phm-models",
    "aeroforge-uq-reports",
    "aeroforge-gdt-annotations",
    "aeroforge-export-packages",
    "aeroforge-backups",
})

MAX_FILE_SIZE = 50 * 1024 * 1024


class MinioObjectStorage:
    def __init__(self):
        self._client = None

    def _ensure_client(self):
        if self._client is not None:
            return self._client
        try:
            from minio import Minio
            endpoint = os.getenv("MINIO_ENDPOINT", "localhost:9000")
            access_key = os.getenv("MINIO_ACCESS_KEY", "aeroforge")
            secret_key = os.getenv("MINIO_SECRET_KEY", "aeroforge123")
            self._client = Minio(
                endpoint,
                access_key=access_key,
                secret_key=secret_key,
                secure=False,
            )
            logger.info(f"MinIO client connected to {endpoint}")
            return self._client
        except Exception as e:
            logger.warning(f"MinIO client init failed: {e}")
            self._client = None
            return None

    async def upload_file(
        self,
        bucket: str,
        file_name: str,
        file_data: bytes,
        content_type: str,
    ) -> dict | None:
        client = self._ensure_client()
        if client is None:
            return None
        if content_type not in ALLOWED_CONTENT_TYPES:
            raise ValueError(f"Unsupported content type: {content_type}")
        if len(file_data) > MAX_FILE_SIZE:
            raise ValueError(f"File size {len(file_data)} exceeds limit {MAX_FILE_SIZE}")
        if bucket not in PREDEFINED_BUCKETS:
            raise ValueError(f"Unknown bucket: {bucket}")
        try:
            file_id = str(uuid.uuid4())
            object_name = f"{file_id}/{file_name}"
            stream = io.BytesIO(file_data)
            client.put_object(
                bucket,
                object_name,
                stream,
                length=len(file_data),
                content_type=content_type,
            )
            return {
                "file_id": file_id,
                "file_name": file_name,
                "bucket": bucket,
                "content_type": content_type,
                "file_size": len(file_data),
                "upload_timestamp": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as e:
            logger.warning(f"MinIO upload failed: {e}")
            return None

    async def get_presigned_url(self, bucket: str, file_id: str, expires_hours: int = 1) -> str | None:
        client = self._ensure_client()
        if client is None:
            return None
        try:
            from datetime import timedelta
            objects = list(client.list_objects(bucket, prefix=f"{file_id}/", recursive=True))
            if not objects:
                return None
            object_name = objects[0].object_name
            url = client.presigned_get_object(
                bucket,
                object_name,
                expires=timedelta(hours=expires_hours),
            )
            return url
        except Exception as e:
            logger.warning(f"MinIO presigned URL failed: {e}")
            return None


object_storage = MinioObjectStorage()