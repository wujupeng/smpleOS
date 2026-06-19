from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_LOCALE = "zh-CN"
SUPPORTED_LOCALES = ["zh-CN", "en-US", "zh-TW"]


class I18nManager:
    _instance: I18nManager | None = None

    def __init__(self) -> None:
        self._translations: dict[str, dict[str, str]] = {}
        self._default_locale = DEFAULT_LOCALE
        self._load_builtin_translations()

    @classmethod
    def get_instance(cls) -> I18nManager:
        if cls._instance is None:
            cls._instance = I18nManager()
        return cls._instance

    def _load_builtin_translations(self) -> None:
        locales_dir = Path(__file__).parent / "locales"
        for locale in SUPPORTED_LOCALES:
            filepath = locales_dir / f"{locale}.json"
            if filepath.exists():
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        self._translations[locale] = json.load(f)
                    logger.info("Loaded %d translations for %s", len(self._translations[locale]), locale)
                except Exception as e:
                    logger.warning("Failed to load translations for %s: %s", locale, e)
            else:
                self._translations[locale] = {}

    def load_translations(self, locale: str, translations: dict[str, str]) -> None:
        self._translations.setdefault(locale, {}).update(translations)

    def t(self, key: str, locale: str | None = None, **kwargs: Any) -> str:
        target_locale = locale or self._default_locale
        translations = self._translations.get(target_locale, {})
        template = translations.get(key)
        if template is None:
            fallback = self._translations.get(self._default_locale, {})
            template = fallback.get(key, key)

        if kwargs:
            try:
                return template.format(**kwargs)
            except (KeyError, IndexError):
                return template

        return template

    def detect_locale(self, accept_language: str | None = None, user_preference: str | None = None, tenant_default: str | None = None) -> str:
        if user_preference and user_preference in SUPPORTED_LOCALES:
            return user_preference
        if tenant_default and tenant_default in SUPPORTED_LOCALES:
            return tenant_default
        if accept_language:
            for lang in accept_language.split(","):
                code = lang.split(";")[0].strip()
                if code in SUPPORTED_LOCALES:
                    return code
                base = code.split("-")[0]
                for supported in SUPPORTED_LOCALES:
                    if supported.startswith(base):
                        return supported
        return self._default_locale

    def get_supported_locales(self) -> list[dict[str, str]]:
        locale_names = {
            "zh-CN": "简体中文",
            "en-US": "English (US)",
            "zh-TW": "繁體中文",
        }
        return [
            {"code": locale, "name": locale_names.get(locale, locale)}
            for locale in SUPPORTED_LOCALES
        ]

    def get_translations(self, locale: str) -> dict[str, str]:
        return self._translations.get(locale, {})

    def update_translation(self, locale: str, key: str, value: str) -> None:
        self._translations.setdefault(locale, {})[key] = value