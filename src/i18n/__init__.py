"""Internationalization (i18n) service for translation management."""

import json
import logging
from enum import Enum
from functools import lru_cache
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class Locale(str, Enum):
    """Supported locales for the application."""

    ZH_CN = "zh-CN"
    EN = "en"


# Supported locales
SUPPORTED_LOCALES = [locale.value for locale in Locale]
DEFAULT_LOCALE = Locale.ZH_CN.value

# Path to locale files
LOCALES_DIR = Path(__file__).parent / "locales"


class I18nService:
    """Service for managing translations."""

    def __init__(self) -> None:
        """Initialize the i18n service and load translations."""
        self._translations: dict[str, dict[str, Any]] = {}
        self._load_all_translations()

    def _load_all_translations(self) -> None:
        """Load all translation files from the locales directory."""
        for locale in SUPPORTED_LOCALES:
            self._translations[locale] = self._load_locale(locale)

    def _load_locale(self, locale: str) -> dict[str, Any]:
        """Load translations for a specific locale.

        Args:
            locale: The locale code (e.g., "zh-CN", "en")

        Returns:
            Dictionary of translations for the locale
        """
        locale_file = LOCALES_DIR / f"{locale}.json"
        if not locale_file.exists():
            return {}

        with open(locale_file, encoding="utf-8") as f:
            return json.load(f)

    def get_translation(
        self,
        key: str,
        locale: str = DEFAULT_LOCALE,
        default: str | None = None,
    ) -> str:
        """Get a translation for a key.

        Args:
            key: Dot-notation key (e.g., "patient.fields.mrn")
            locale: Locale code (defaults to zh-CN)
            default: Default value if key not found

        Returns:
            The translated string, or default/key if not found
        """
        # Validate locale
        if locale not in SUPPORTED_LOCALES:
            locale = DEFAULT_LOCALE

        translations = self._translations.get(locale, {})

        # Navigate through nested keys
        keys = key.split(".")
        value: Any = translations
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                # Try fallback to English
                if locale != "en":
                    return self.get_translation(key, "en", default)
                return default if default is not None else key

        if isinstance(value, str):
            return value
        return default if default is not None else key

    def get_all_translations(self, locale: str = DEFAULT_LOCALE) -> dict[str, Any]:
        """Get all translations for a locale.

        Args:
            locale: Locale code (defaults to zh-CN)

        Returns:
            Dictionary of all translations for the locale
        """
        if locale not in SUPPORTED_LOCALES:
            locale = DEFAULT_LOCALE
        return self._translations.get(locale, {})

    def get_nested(
        self,
        key: str,
        locale: str = DEFAULT_LOCALE,
    ) -> dict[str, Any] | str | None:
        """Get a nested translation object.

        Args:
            key: Dot-notation key (e.g., "patient.timeline.phases")
            locale: Locale code

        Returns:
            The nested object or string, or None if not found
        """
        if locale not in SUPPORTED_LOCALES:
            locale = DEFAULT_LOCALE

        translations = self._translations.get(locale, {})

        keys = key.split(".")
        value: Any = translations
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return None

        return value

    def reload(self) -> None:
        """Reload all translations from disk."""
        self._translations.clear()
        self._load_all_translations()


@lru_cache
def get_i18n_service() -> I18nService:
    """Get the singleton i18n service instance.

    Returns:
        The I18nService singleton
    """
    return I18nService()


def t(key: str, locale: str = DEFAULT_LOCALE, default: str | None = None) -> str:
    """Shorthand function for getting translations.

    Args:
        key: Dot-notation key (e.g., "common.save")
        locale: Locale code
        default: Default value if key not found

    Returns:
        The translated string
    """
    return get_i18n_service().get_translation(key, locale, default)
