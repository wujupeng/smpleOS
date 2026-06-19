import pytest

from aeroforge_common.i18n.manager import I18nManager, DEFAULT_LOCALE, SUPPORTED_LOCALES


class TestI18nManager:
    def test_singleton(self) -> None:
        m1 = I18nManager.get_instance()
        m2 = I18nManager.get_instance()
        assert m1 is m2

    def test_translate_zh_cn(self) -> None:
        manager = I18nManager()
        result = manager.t("common.save", "zh-CN")
        assert result == "保存"

    def test_translate_en_us(self) -> None:
        manager = I18nManager()
        result = manager.t("common.save", "en-US")
        assert result == "Save"

    def test_translate_with_interpolation(self) -> None:
        manager = I18nManager()
        manager.load_translations("zh-CN", {"greeting": "你好, {name}!"})
        result = manager.t("greeting", "zh-CN", name="AeroForge")
        assert result == "你好, AeroForge!"

    def test_translate_missing_key_fallback(self) -> None:
        manager = I18nManager()
        manager.load_translations("zh-CN", {"test.key": "测试值"})
        result = manager.t("test.key", "en-US")
        assert result == "测试值"

    def test_translate_missing_key_returns_key(self) -> None:
        manager = I18nManager()
        result = manager.t("nonexistent.key", "zh-CN")
        assert result == "nonexistent.key"

    def test_detect_locale_user_preference(self) -> None:
        manager = I18nManager()
        result = manager.detect_locale(user_preference="en-US")
        assert result == "en-US"

    def test_detect_locale_accept_language(self) -> None:
        manager = I18nManager()
        result = manager.detect_locale(accept_language="en-US,zh-CN;q=0.9")
        assert result == "en-US"

    def test_detect_locale_accept_language_base(self) -> None:
        manager = I18nManager()
        result = manager.detect_locale(accept_language="en")
        assert result == "en-US"

    def test_detect_locale_tenant_default(self) -> None:
        manager = I18nManager()
        result = manager.detect_locale(tenant_default="en-US")
        assert result == "en-US"

    def test_detect_locale_default(self) -> None:
        manager = I18nManager()
        result = manager.detect_locale()
        assert result == DEFAULT_LOCALE

    def test_detect_locale_priority(self) -> None:
        manager = I18nManager()
        result = manager.detect_locale(
            accept_language="en-US",
            user_preference="zh-CN",
            tenant_default="en-US",
        )
        assert result == "zh-CN"

    def test_get_supported_locales(self) -> None:
        manager = I18nManager()
        locales = manager.get_supported_locales()
        assert len(locales) == len(SUPPORTED_LOCALES)
        codes = [l["code"] for l in locales]
        assert "zh-CN" in codes
        assert "en-US" in codes

    def test_get_translations(self) -> None:
        manager = I18nManager()
        translations = manager.get_translations("zh-CN")
        assert isinstance(translations, dict)
        assert "common.save" in translations

    def test_update_translation(self) -> None:
        manager = I18nManager()
        manager.update_translation("zh-CN", "custom.key", "自定义值")
        result = manager.t("custom.key", "zh-CN")
        assert result == "自定义值"

    def test_load_translations(self) -> None:
        manager = I18nManager()
        manager.load_translations("fr-FR", {"hello": "Bonjour"})
        result = manager.t("hello", "fr-FR")
        assert result == "Bonjour"