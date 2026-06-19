from __future__ import annotations

from functools import wraps
from typing import Any, Callable

from fastapi import HTTPException, Request

from .models import AeroForgeRole, ROLE_PERMISSIONS, AuthUser


def _extract_user_from_request(request: Request) -> AuthUser:
    user = getattr(request.state, "user", None)
    if user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    if not isinstance(user, AuthUser):
        raise HTTPException(status_code=401, detail="Invalid authentication data")
    return user


def require_role(*roles: str) -> Callable:
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            request: Request | None = kwargs.get("request")
            if request is None:
                for arg in args:
                    if isinstance(arg, Request):
                        request = arg
                        break
            if request is None:
                raise HTTPException(status_code=500, detail="Request object not found")

            user = _extract_user_from_request(request)
            if not any(user.has_role(role) for role in roles):
                raise HTTPException(
                    status_code=403,
                    detail=f"Required role: {' or '.join(roles)}",
                )
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def require_permission(permission: str) -> Callable:
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            request: Request | None = kwargs.get("request")
            if request is None:
                for arg in args:
                    if isinstance(arg, Request):
                        request = arg
                        break
            if request is None:
                raise HTTPException(status_code=500, detail="Request object not found")

            user = _extract_user_from_request(request)
            if not user.has_permission(permission):
                raise HTTPException(
                    status_code=403,
                    detail=f"Required permission: {permission}",
                )
            return await func(*args, **kwargs)
        return wrapper
    return decorator