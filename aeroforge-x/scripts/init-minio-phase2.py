"""Initialize MinIO buckets for Phase 2 CAE services."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "libs", "aeroforge-db", "src"))

from minio import Minio
from minio.error import S3Error


def init_minio_buckets() -> None:
    endpoint = os.getenv("MINIO_ENDPOINT", "localhost:9000")
    access_key = os.getenv("MINIO_ROOT_USER", "aeroforge_minio")
    secret_key = os.getenv("MINIO_ROOT_PASSWORD", "aeroforge_minio_secret")
    secure = os.getenv("MINIO_SECURE", "false").lower() == "true"

    client = Minio(endpoint, access_key=access_key, secret_key=secret_key, secure=secure)

    buckets = [
        "aeroforge-mesh",
        "aeroforge-cae-results",
        "aeroforge-cfd-cases",
        "aeroforge-fea-results",
        "aeroforge-reports",
    ]

    for bucket_name in buckets:
        try:
            if not client.bucket_exists(bucket_name):
                client.make_bucket(bucket_name)
                print(f"Created bucket: {bucket_name}")
            else:
                print(f"Bucket already exists: {bucket_name}")
        except S3Error as e:
            print(f"Error creating bucket {bucket_name}: {e}")


if __name__ == "__main__":
    init_minio_buckets()