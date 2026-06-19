"""Phase 3 MinIO Bucket Initialization Script

Creates buckets for Phase 3 features:
- aeroforge-supplier: supplier documents and certificates
- aeroforge-reports: generated reports and analytics
"""

from minio import Minio

MINIO_ENDPOINT = "localhost:9000"
MINIO_ACCESS_KEY = "aeroforge_minio"
MINIO_SECRET_KEY = "aeroforge_minio_secret"

PHASE3_BUCKETS = [
    "aeroforge-supplier",
    "aeroforge-reports",
    "aeroforge-ai-proposals",
    "aeroforge-optimization",
]


def init_phase3_buckets() -> None:
    client = Minio(
        MINIO_ENDPOINT,
        access_key=MINIO_ACCESS_KEY,
        secret_key=MINIO_SECRET_KEY,
        secure=False,
    )

    for bucket_name in PHASE3_BUCKETS:
        if not client.bucket_exists(bucket_name):
            client.make_bucket(bucket_name)
            print(f"Created bucket: {bucket_name}")
        else:
            print(f"Bucket already exists: {bucket_name}")

    print("Phase 3 MinIO initialization complete")


if __name__ == "__main__":
    init_phase3_buckets()