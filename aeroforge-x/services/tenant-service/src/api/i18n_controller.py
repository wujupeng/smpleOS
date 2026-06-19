from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Header
from pydantic import BaseModel, Field

from aeroforge_common.domain.responses import ApiResponse
from aeroforge_common.i18n import I18nManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/i18n", tags=["i18n"])

_manager = I18nManager.get_instance()


class UpdateTranslationRequest(BaseModel):
    value: str = Field(..., min_length=0)


@router.get("/locales", response_model=ApiResponse[dict])
async def get_supported_locales():
    locales = _manager.get_supported_locales()
    return ApiResponse(data={
        "default": "zh-CN",
        "locales": locales,
    })


@router.get("/translations/{locale}", response_model=ApiResponse[dict])
async def get_translations(locale: str):
    translations = _manager.get_translations(locale)
    return ApiResponse(data={
        "locale": locale,
        "total": len(translations),
        "translations": translations,
    })


@router.put("/translations/{locale}/{key:path}", response_model=ApiResponse[dict])
async def update_translation(locale: str, key: str, body: UpdateTranslationRequest):
    _manager.update_translation(locale, key, body.value)
    return ApiResponse(data={
        "locale": locale,
        "key": key,
        "value": body.value,
    })


@router.post("/detect-locale", response_model=ApiResponse[dict])
async def detect_locale(
    accept_language: str | None = Header(None, alias="Accept-Language"),
):
    detected = _manager.detect_locale(accept_language=accept_language)
    return ApiResponse(data={
        "detected_locale": detected,
        "accept_language": accept_language,
    })


@router.get("/translate", response_model=ApiResponse[dict])
async def translate_key(
    key: str,
    locale: str | None = None,
    accept_language: str | None = Header(None, alias="Accept-Language"),
):
    detected = _manager.detect_locale(accept_language=accept_language, user_preference=locale)
    translated = _manager.t(key, detected)
    return ApiResponse(data={
        "key": key,
        "locale": detected,
        "translation": translated,
    })