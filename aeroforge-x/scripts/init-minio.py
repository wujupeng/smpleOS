#!/usr/bin/env python3
"""Initialize MinIO buckets for AeroForge-X."""

from minio import Minio


def main() -> None:
    client = Minio(
        "localhost:9000",
        access_key="aeroforge_minio",
        secret_key="aeroforge_minio_secret",
        secure=False,
    )

    buckets = [
        "aeroforge-models",
        "aeroforge-attachments",
        "aeroforge-cae-results",
        "aeroforge-documents",
        "aeroforge-exports",
    ]

    for bucket in buckets:
        if not client.bucket_exists(bucket):
            client.make_bucket(bucket)
            print(f"Created bucket: {bucket}")
        else:
            print(f"Bucket already exists: {bucket}")


if __name__ == "__main__":
    main()