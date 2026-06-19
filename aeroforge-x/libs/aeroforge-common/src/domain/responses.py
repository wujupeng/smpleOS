from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Generic, TypeVar
from uuid import uuid4

from pydantic import BaseModel

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    code: int = 0
    message: str = "success"
    data: T | None = None
    timestamp: str = ""
    request_id: str = ""

    def __init__(self, **data: Any) -> None:
        super().__init__(**data)
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()
        if not self.request_id:
            self.request_id = str(uuid4())


class PagedResponse(BaseModel, Generic[T]):
    code: int = 0
    message: str = "success"
    data: list[T] = []
    total: int = 0
    page: int = 1
    page_size: int = 20
    timestamp: str = ""
    request_id: str = ""

    def __init__(self, **data: Any) -> None:
        super().__init__(**data)
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()
        if not self.request_id:
            self.request_id = str(uuid4())

    @property
    def total_pages(self) -> int:
        if self.page_size <= 0:
            return 0
        return (self.total + self.page_size - 1) // self.page_size


class AsyncTaskResponse(BaseModel):
    code: int = 0
    message: str = "Task submitted"
    task_id: str = ""
    status: str = "queued"
    timestamp: str = ""
    request_id: str = ""

    def __init__(self, **data: Any) -> None:
        super().__init__(**data)
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()
        if not self.request_id:
            self.request_id = str(uuid4())


class BusinessError(Exception):
    def __init__(self, message: str, code: int = 400, details: dict[str, Any] | None = None) -> None:
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(message)


class NotFoundError(BusinessError):
    def __init__(self, resource: str, resource_id: str = "") -> None:
        msg = f"{resource} not found"
        if resource_id:
            msg = f"{resource} '{resource_id}' not found"
        super().__init__(message=msg, code=404)


class ValidationError(BusinessError):
    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message=message, code=422, details=details)


class ForbiddenError(BusinessError):
    def __init__(self, message: str = "Forbidden") -> None:
        super().__init__(message=message, code=403)


class UnauthorizedError(BusinessError):
    def __init__(self, message: str = "Unauthorized") -> None:
        super().__init__(message=message, code=401)