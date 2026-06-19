from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import Request

logger = logging.getLogger("aeroforge.audit")


class AuditLogger:
    @staticmethod
    def log_operation(
        user_id: str,
        action: str,
        resource_type: str,
        resource_id: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user_id": user_id,
            "action": action,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "details": details or {},
        }
        logger.info("AUDIT: %s", log_entry)

    @staticmethod
    def log_design_change(user_id: str, spec_id: str, change_type: str, details: dict[str, Any]) -> None:
        AuditLogger.log_operation(user_id, "design_change", "aircraft_spec", spec_id, {"change_type": change_type, **details})

    @staticmethod
    def log_approval(user_id: str, resource_type: str, resource_id: str, decision: str) -> None:
        AuditLogger.log_operation(user_id, "approval", resource_type, resource_id, {"decision": decision})

    @staticmethod
    def log_inspection(user_id: str, item_code: str, inspection_type: str, result: str) -> None:
        AuditLogger.log_operation(user_id, "inspection", inspection_type, item_code, {"result": result})


async def audit_middleware(request: Request, call_next):
    response = await call_next(request)

    if request.method in ("POST", "PUT", "DELETE") and "/api/v1/" in str(request.url):
        user = getattr(request.state, "user", None)
        user_id = user.user_id if user else "anonymous"
        AuditLogger.log_operation(
            user_id=user_id,
            action=f"{request.method} {request.url.path}",
            resource_type="api",
            resource_id="",
        )

    return response