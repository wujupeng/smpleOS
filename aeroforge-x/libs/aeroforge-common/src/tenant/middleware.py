from __future__ import annotations

import logging
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from .context import TenantContext, TenantInfo, set_tenant_context, clear_tenant_context

logger = logging.getLogger(__name__)

TENANT_ID_HEADER = "X-Tenant-Id"
TENANT_CODE_HEADER = "X-Tenant-Code"

PUBLIC_PATHS = {
    "/api/v1/auth/login",
    "/api/v1/auth/token",
    "/api/v1/health",
    "/docs",
    "/openapi.json",
    "/redoc",
}

SYSTEM_TENANT_ID = "system"


class TenantMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: Any, tenant_resolver: Any | None = None) -> None:
        super().__init__(app)
        self._tenant_resolver = tenant_resolver

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        path = request.url.path

        if path in PUBLIC_PATHS or path.startswith("/api/v1/tenants") and request.method == "POST":
            response = await call_next(request)
            return response

        tenant_id = request.headers.get(TENANT_ID_HEADER)
        tenant_code = request.headers.get(TENANT_CODE_HEADER)

        if not tenant_id:
            user = getattr(request.state, "user", None)
            if user and hasattr(user, "tenant_id"):
                tenant_id = user.tenant_id
                tenant_code = getattr(user, "tenant_code", None)

        if not tenant_id:
            if self._is_tenant_optional_path(path):
                clear_tenant_context()
                response = await call_next(request)
                return response
            return JSONResponse(
                status_code=400,
                content={"code": 400, "message": "Tenant ID required. Set X-Tenant-Id header."},
            )

        if not tenant_code:
            tenant_code = tenant_id

        info = set_tenant_context(
            tenant_id=tenant_id,
            tenant_code=tenant_code,
        )

        if info.status == "suspended":
            clear_tenant_context()
            return JSONResponse(
                status_code=403,
                content={"code": 403, "message": "Tenant is suspended. Contact administrator."},
            )

        try:
            response = await call_next(request)
        finally:
            clear_tenant_context()

        return response

    def _is_tenant_optional_path(self, path: str) -> bool:
        tenant_optional_prefixes = [
            "/api/v1/auth",
            "/api/v1/health",
        ]
        return any(path.startswith(prefix) for prefix in tenant_optional_prefixes)