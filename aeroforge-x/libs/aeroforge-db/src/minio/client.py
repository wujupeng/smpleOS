from __future__ import annotations

from io import BytesIO

from minio import Minio
from pydantic_settings import BaseSettings


class MinioSettings(BaseSettings):
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "aeroforge_minio"
    minio_secret_key: str = "aeroforge_minio_secret"
    minio_secure: bool = False

    model_config = {"env_prefix": ""}


_settings = MinioSettings()
_client: Minio | None = None


def get_client() -> Minio:
    global _client
    if _client is None:
        _client = Minio(
            _settings.minio_endpoint,
            access_key=_settings.minio_access_key,
            secret_key=_settings.minio_secret_key,
            secure=_settings.minio_secure,
        )
    return _client


def ensure_bucket(bucket_name: str) -> None:
    client = get_client()
    if not client.bucket_exists(bucket_name):
        client.make_bucket(bucket_name)


def upload_file(bucket_name: str, object_key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
    client = get_client()
    ensure_bucket(bucket_name)
    client.put_object(
        bucket_name,
        object_key,
        BytesIO(data),
        length=len(data),
        content_type=content_type,
    )
    return object_key


def download_file(bucket_name: str, object_key: str) -> bytes:
    client = get_client()
    response = client.get_object(bucket_name, object_key)
    try:
        return response.read()
    finally:
        response.close()
        response.release_conn()


def get_presigned_url(bucket_name: str, object_key: str, expires: int = 3600) -> str:
    from datetime import timedelta

    client = get_client()
    return client.presigned_get_object(bucket_name, object_key, expires=timedelta(seconds=expires))