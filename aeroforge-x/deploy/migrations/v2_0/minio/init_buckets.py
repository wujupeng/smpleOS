from minio import Minio
from minio.error import S3Error


def init_buckets():
    client = Minio(
        "localhost:9000",
        access_key="minioadmin",
        secret_key="minioadmin",
        secure=False
    )

    buckets = [
        "physics-models",
        "simulation-results",
        "rom-models",
        "calibration-data"
    ]

    for bucket in buckets:
        try:
            if not client.bucket_exists(bucket):
                client.make_bucket(bucket)
                print(f"Created bucket: {bucket}")
                versioning_cfg = {"Status": "Enabled"}
                client.set_bucket_versioning(bucket, versioning_cfg)
                print(f"Enabled versioning for bucket: {bucket}")
            else:
                print(f"Bucket already exists: {bucket}")
        except S3Error as e:
            print(f"Error creating bucket {bucket}: {e}")


if __name__ == "__main__":
    init_buckets()