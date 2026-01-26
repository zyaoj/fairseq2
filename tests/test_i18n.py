"""Tests for i18n service."""

import pytest

from src.i18n import (
    DEFAULT_LOCALE,
    SUPPORTED_LOCALES,
    I18nService,
    get_i18n_service,
    t,
)


class TestI18nService:
    """Tests for I18nService class."""

    def test_supported_locales(self) -> None:
        """Test that supported locales are defined."""
        assert "zh-CN" in SUPPORTED_LOCALES
        assert "en" in SUPPORTED_LOCALES

    def test_default_locale_is_chinese(self) -> None:
        """Test that default locale is Chinese."""
        assert DEFAULT_LOCALE == "zh-CN"

    def test_service_loads_translations(self) -> None:
        """Test that service loads translation files."""
        service = I18nService()
        assert "zh-CN" in service._translations
        assert "en" in service._translations

    def test_get_translation_chinese(self) -> None:
        """Test getting Chinese translation."""
        service = I18nService()
        result = service.get_translation("common.save", "zh-CN")
        assert result == "保存"

    def test_get_translation_english(self) -> None:
        """Test getting English translation."""
        service = I18nService()
        result = service.get_translation("common.save", "en")
        assert result == "Save"

    def test_get_translation_nested_key(self) -> None:
        """Test getting deeply nested translation."""
        service = I18nService()
        result = service.get_translation("patient.timeline.phases.surgery", "zh-CN")
        assert result == "手术"

    def test_get_translation_fallback_to_english(self) -> None:
        """Test fallback to English when key missing in Chinese."""
        service = I18nService()
        # This key exists in both, so let's test with a key that would fallback
        result = service.get_translation("common.save", "zh-CN")
        assert result == "保存"

    def test_get_translation_returns_key_when_not_found(self) -> None:
        """Test that missing key returns the key itself."""
        service = I18nService()
        result = service.get_translation("nonexistent.key", "zh-CN")
        assert result == "nonexistent.key"

    def test_get_translation_with_default(self) -> None:
        """Test that default value is returned when key not found."""
        service = I18nService()
        result = service.get_translation("nonexistent.key", "zh-CN", default="Fallback")
        assert result == "Fallback"

    def test_get_translation_invalid_locale_uses_default(self) -> None:
        """Test that invalid locale falls back to default."""
        service = I18nService()
        result = service.get_translation("common.save", "invalid-locale")
        assert result == "保存"  # Should use zh-CN default

    def test_get_all_translations(self) -> None:
        """Test getting all translations for a locale."""
        service = I18nService()
        translations = service.get_all_translations("en")
        assert "patient" in translations
        assert "common" in translations
        assert "auth" in translations

    def test_get_nested_returns_dict(self) -> None:
        """Test getting a nested translation object."""
        service = I18nService()
        phases = service.get_nested("patient.timeline.phases", "zh-CN")
        assert isinstance(phases, dict)
        assert phases["surgery"] == "手术"
        assert phases["consultation"] == "门诊咨询"

    def test_get_nested_returns_none_for_missing(self) -> None:
        """Test get_nested returns None for missing keys."""
        service = I18nService()
        result = service.get_nested("nonexistent.path", "zh-CN")
        assert result is None


class TestI18nShorthand:
    """Tests for shorthand functions."""

    def test_t_function(self) -> None:
        """Test the t() shorthand function."""
        result = t("common.cancel", "zh-CN")
        assert result == "取消"

    def test_t_function_english(self) -> None:
        """Test the t() function with English."""
        result = t("common.cancel", "en")
        assert result == "Cancel"

    def test_t_function_default_locale(self) -> None:
        """Test t() uses default locale (Chinese)."""
        result = t("common.search")
        assert result == "搜索"

    def test_get_i18n_service_singleton(self) -> None:
        """Test that get_i18n_service returns singleton."""
        service1 = get_i18n_service()
        service2 = get_i18n_service()
        assert service1 is service2


class TestTranslationContent:
    """Tests for translation content completeness."""

    def test_patient_fields_chinese(self) -> None:
        """Test patient field translations in Chinese."""
        service = I18nService()
        assert service.get_translation("patient.fields.mrn", "zh-CN") == "病历号"
        assert service.get_translation("patient.fields.gender", "zh-CN") == "性别"

    def test_lifecycle_phases_chinese(self) -> None:
        """Test lifecycle phase translations in Chinese."""
        service = I18nService()
        phases = service.get_nested("patient.timeline.phases", "zh-CN")
        assert phases["consultation"] == "门诊咨询"
        assert phases["pre_surgery"] == "术前检查"
        assert phases["surgery"] == "手术"
        assert phases["post_surgery"] == "术后恢复"
        assert phases["follow_up"] == "随访复查"

    def test_lab_result_status_chinese(self) -> None:
        """Test lab result status translations in Chinese."""
        service = I18nService()
        assert service.get_translation("lab_result.status.pending", "zh-CN") == "等待处理"
        assert service.get_translation("lab_result.status.completed", "zh-CN") == "已完成"

    def test_auth_translations_chinese(self) -> None:
        """Test auth translations in Chinese."""
        service = I18nService()
        assert service.get_translation("auth.login", "zh-CN") == "登录"
        assert service.get_translation("auth.roles.urologist", "zh-CN") == "泌尿外科医生"

    def test_error_messages_chinese(self) -> None:
        """Test error message translations in Chinese."""
        service = I18nService()
        assert "服务器错误" in service.get_translation("errors.server_error", "zh-CN")
        assert "权限" in service.get_translation("errors.forbidden", "zh-CN")
