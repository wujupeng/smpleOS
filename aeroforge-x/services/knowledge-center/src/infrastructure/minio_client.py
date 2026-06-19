import os
import io
from typing import Optional

from minio import Minio


class MinioClient:
    def __init__(self):
        self._client: Optional[Minio] = None
        self._endpoint = os.getenv("MINIO_ENDPOINT", "minio:9000")
        self._access_key = os.getenv("MINIO_ACCESS_KEY", "aeroforge_minio")
        self._secret_key = os.getenv("MINIO_SECRET_KEY", "aeroforge_minio_secret")
        self._secure = os.getenv("MINIO_SECURE", "false").lower() == "true"

    async def connect(self):
        self._client = Minio(
            self._endpoint,
            access_key=self._access_key,
            secret_key=self._secret_key,
            secure=self._secure,
        )
        self._ensure_buckets()

    def _ensure_buckets(self):
        buckets = [
            "aeroforge-knowledge-snapshots",
            "aeroforge-knowledge-exports",
            "aeroforge-knowledge-embeddings",
        ]
        for bucket in buckets:
            if not self._client.bucket_exists(bucket):
                self._client.make_bucket(bucket)

    def is_connected(self) -> bool:
        return self._client is not None

    def get_client(self) -> Minio:
        if not self._client:
            raise RuntimeError("MinIO client not initialized")
        return self._client

    def upload_bytes(self, bucket: str, object_name: str, data: bytes, content_type: str = "application/octet-stream"):
        self._client.put_object(
            bucket, object_name, io.BytesIO(data), len(data), content_type=content_type
        )

    def download_bytes(self, bucket: str, object_name: str) -> bytes:
        response = self._client.get_object(bucket, object_name)
        data = response.read()
        response.close()
        response.release_conn()
        return data