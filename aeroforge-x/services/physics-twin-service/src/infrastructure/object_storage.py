import io
import os
from typing import BinaryIO

from minio import Minio
from minio.error import S3Error


class ObjectStorage:
    def __init__(self):
        self._client = Minio(
            os.getenv("MINIO_ENDPOINT", "localhost:9000"),
            access_key=os.getenv("MINIO_ACCESS_KEY", "minioadmin"),
            secret_key=os.getenv("MINIO_SECRET_KEY", "minioadmin"),
            secure=False
        )

    def upload(self, bucket: str, object_name: str, data: BinaryIO, length: int, content_type: str = "application/octet-stream") -> str:
        try:
            self._client.put_object(bucket, object_name, data, length, content_type=content_type)
            return object_name
        except S3Error as e:
            raise RuntimeError(f"Failed to upload object {object_name} to bucket {bucket}: {e}")

    def download(self, bucket: str, object_name: str) -> bytes:
        try:
            response = self._client.get_object(bucket, object_name)
            data = response.read()
            response.close()
            response.release_conn()
            return data
        except S3Error as e:
            raise RuntimeError(f"Failed to download object {object_name} from bucket {bucket}: {e}")

    def delete(self, bucket: str, object_name: str) -> None:
        try:
            self._client.remove_object(bucket, object_name)
        except S3Error as e:
            raise RuntimeError(f"Failed to delete object {object_name} from bucket {bucket}: {e}")

    def get_presigned_url(self, bucket: str, object_name: str, expires: int = 3600) -> str:
        try:
            return self._client.presigned_get_object(bucket, object_name, expires=expires)
        except S3Error as e:
            raise RuntimeError(f"Failed to generate presigned URL for {object_name}: {e}")


object_storage = ObjectStorage()