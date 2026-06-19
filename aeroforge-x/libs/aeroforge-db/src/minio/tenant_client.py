from __future__ import annotations

import logging

from aeroforge_common.tenant.context import TenantContext

from .client import get_client, ensure_bucket

logger = logging.getLogger(__name__)


def get_tenant_object_key(tenant_id: str | None, object_key: str) -> str:
    prefix = f"{tenant_id}/" if tenant_id else ""
    return f"{prefix}{object_key}"


def get_current_tenant_object_key(object_key: str) -> str:
    info = TenantContext.get()
    return get_tenant_object_key(info.tenant_id if info else None, object_key)


def tenant_upload_file(bucket_name: str, object_key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
    tenant_key = get_current_tenant_object_key(object_key)
    from .client import upload_file
    return upload_file(bucket_name, tenant_key, data, content_type)


def tenant_download_file(bucket_name: str, object_key: str) -> bytes:
    tenant_key = get_current_tenant_object_key(object_key)
    from .client import download_file
    return download_file(bucket_name, tenant_key)


def create_tenant_bucket_structure(tenant_id: str) -> None:
    client = get_client()
    buckets = ["aeroforge-designs", "aeroforge-cae-results", "aeroforge-reports", "aeroforge-deliveries"]
    for bucket in buckets:
        ensure_bucket(bucket)
        placeholder_key = f"{tenant_id}/.tenant_init"
        from io import BytesIO
        client.put_object(
            bucket,
            placeholder_key,
            BytesIO(b"tenant_initialized"),
            length=18,
            content_type="text/plain",
        )
    logger.info("Created MinIO tenant structure for %s", tenant_id)


def remove_tenant_objects(tenant_id: str) -> None:
    client = get_client()
    buckets = ["aeroforge-designs", "aeroforge-cae-results", "aeroforge-reports", "aeroforge-deliveries"]
    prefix = f"{tenant_id}/"
    for bucket in buckets:
        try:
            objects = client.list_objects(bucket, prefix=prefix, recursive=True)
            for obj in objects:
                client.remove_object(bucket, obj.object_name)
        except Exception as e:
            logger.warning("Failed to remove tenant objects from %s: %s", bucket, e)
    logger.info("Removed MinIO tenant objects for %s", tenant_id)