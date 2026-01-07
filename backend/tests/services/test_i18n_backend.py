"""
Tests for Internationalization (i18n) Backend Service.

Verifies:
- Translation management
- Locale handling
- Variable interpolation
- Pluralization
- Date/time/number formatting
- Import/export
- Missing translation tracking
"""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from sensei.services.i18n_backend import (
    I18nBackendService,
    Locale,
    LocaleConfig,
    MissingTranslation,
    PluralCategory,
    TranslationExport,
    TranslationKey,
    TranslationNamespace,
)


class TestLocaleConfiguration:
    """Tests for locale configuration."""
    
    def test_get_supported_locales(self) -> None:
        """Test getting list of supported locales."""
        service = I18nBackendService()
        
        locales = service.get_supported_locales()
        
        assert len(locales) > 0
        assert any(loc.code == "en" for loc in locales)
        assert any(loc.code == "fr" for loc in locales)
    
    def test_get_locale_config(self) -> None:
        """Test getting configuration for a specific locale."""
        service = I18nBackendService()
        
        en_config = service.get_locale_config("en")
        
        assert en_config is not None
        assert en_config.code == "en"
        assert en_config.name == "English"
    
    def test_locale_config_properties(self) -> None:
        """Test locale configuration properties."""
        service = I18nBackendService()
        
        fr_config = service.get_locale_config("fr")
        
        assert fr_config is not None
        assert fr_config.native_name == "Français"
        assert fr_config.direction == "ltr"
        assert fr_config.number_decimal == ","
        assert fr_config.first_day_of_week == 1
    
    def test_arabic_rtl_config(self) -> None:
        """Test Arabic right-to-left configuration."""
        service = I18nBackendService()
        
        ar_config = service.get_locale_config("ar")
        
        assert ar_config is not None
        assert ar_config.direction == "rtl"
    
    def test_enable_disable_locale(self) -> None:
        """Test enabling and disabling a locale."""
        service = I18nBackendService()
        
        # Disable French
        result = service.set_locale_enabled("fr", False)
        
        assert result is True
        
        enabled = service.get_supported_locales()
        assert not any(loc.code == "fr" for loc in enabled)
        
        # Re-enable
        service.set_locale_enabled("fr", True)
        enabled = service.get_supported_locales()
        assert any(loc.code == "fr" for loc in enabled)


class TestBasicTranslation:
    """Tests for basic translation functionality."""
    
    def test_translate_key(self) -> None:
        """Test translating a key to default locale."""
        service = I18nBackendService()
        
        result = service.translate("common.save")
        
        assert result == "Save"
    
    def test_translate_to_french(self) -> None:
        """Test translating to French."""
        service = I18nBackendService()
        
        result = service.translate("common.save", locale="fr")
        
        assert result == "Enregistrer"
    
    def test_translate_shorthand(self) -> None:
        """Test shorthand t() method."""
        service = I18nBackendService()
        
        result = service.t("common.cancel", locale="fr")
        
        assert result == "Annuler"
    
    def test_translate_missing_key(self) -> None:
        """Test translation with missing key."""
        service = I18nBackendService()
        
        result = service.translate("missing.key")
        
        assert result == "missing.key"
    
    def test_translate_with_default(self) -> None:
        """Test translation with default value."""
        service = I18nBackendService()
        
        result = service.translate(
            "missing.key",
            default="Default Value",
        )
        
        assert result == "Default Value"
    
    def test_fallback_to_default_locale(self) -> None:
        """Test fallback when translation missing in target locale."""
        service = I18nBackendService()
        
        # Add key with only English translation
        service.add_translation(
            key="test.fallback",
            namespace=TranslationNamespace.COMMON,
            translations={"en": "English Only"},
        )
        
        # Request French - should fallback to English
        result = service.translate("test.fallback", locale="fr")
        
        assert result == "English Only"


class TestInterpolation:
    """Tests for variable interpolation."""
    
    def test_interpolate_string(self) -> None:
        """Test string variable interpolation."""
        service = I18nBackendService()
        
        service.add_translation(
            key="greeting",
            namespace=TranslationNamespace.MESSAGES,
            translations={"en": "Hello, {name}!"},
        )
        
        result = service.translate(
            "greeting",
            variables={"name": "John"},
        )
        
        assert result == "Hello, John!"
    
    def test_interpolate_multiple_variables(self) -> None:
        """Test multiple variable interpolation."""
        service = I18nBackendService()
        
        service.add_translation(
            key="welcome",
            namespace=TranslationNamespace.MESSAGES,
            translations={"en": "Welcome {user} to {company}"},
        )
        
        result = service.translate(
            "welcome",
            variables={"user": "Alice", "company": "Acme Corp"},
        )
        
        assert result == "Welcome Alice to Acme Corp"
    
    def test_interpolate_number(self) -> None:
        """Test number interpolation with formatting."""
        service = I18nBackendService()
        
        service.add_translation(
            key="count_message",
            namespace=TranslationNamespace.MESSAGES,
            translations={"en": "You have {count} items"},
        )
        
        result = service.translate(
            "count_message",
            variables={"count": 1500},
        )
        
        # Number should be formatted
        assert "1,500" in result or "1500" in result
    
    def test_interpolate_with_shorthand(self) -> None:
        """Test interpolation with t() shorthand."""
        service = I18nBackendService()
        
        service.add_translation(
            key="hello",
            namespace=TranslationNamespace.COMMON,
            translations={"en": "Hello {name}"},
        )
        
        result = service.t("hello", name="World")
        
        assert result == "Hello World"


class TestPluralization:
    """Tests for pluralization."""
    
    def test_plural_translation(self) -> None:
        """Test basic pluralization."""
        service = I18nBackendService()
        
        key = service.add_translation(
            key="items",
            namespace=TranslationNamespace.COMMON,
            translations={"en": "{count} items"},
        )
        
        service.add_plural_translation(
            "items",
            "en",
            {"one": "{count} item", "other": "{count} items"},
        )
        
        result_one = service.translate("items", count=1)
        result_many = service.translate("items", count=5)
        
        assert "1 item" in result_one
        assert "5 items" in result_many
    
    def test_plural_french_rules(self) -> None:
        """Test French pluralization (0 and 1 are singular)."""
        service = I18nBackendService()
        
        service.add_translation(
            key="fichiers",
            namespace=TranslationNamespace.COMMON,
            translations={"fr": "{count} fichiers"},
        )
        
        service.add_plural_translation(
            "fichiers",
            "fr",
            {"one": "{count} fichier", "other": "{count} fichiers"},
        )
        
        result_zero = service.translate("fichiers", locale="fr", count=0)
        result_one = service.translate("fichiers", locale="fr", count=1)
        
        # In French, 0 is treated as singular
        assert "fichier" in result_zero and "fichiers" not in result_zero
        assert "fichier" in result_one and "fichiers" not in result_one


class TestAddAndUpdateTranslations:
    """Tests for adding and updating translations."""
    
    def test_add_translation(self) -> None:
        """Test adding a new translation."""
        service = I18nBackendService()
        
        key = service.add_translation(
            key="custom.key",
            namespace=TranslationNamespace.COMMON,
            translations={"en": "English", "fr": "Français"},
            description="A custom key",
        )
        
        assert key.id is not None
        assert key.key == "custom.key"
        assert service.translate("custom.key") == "English"
    
    def test_update_translation(self) -> None:
        """Test updating a translation."""
        service = I18nBackendService()
        
        result = service.update_translation(
            "common.save",
            "en",
            "Save Changes",
        )
        
        assert result is True
        assert service.translate("common.save") == "Save Changes"
    
    def test_update_nonexistent_key(self) -> None:
        """Test updating a non-existent key."""
        service = I18nBackendService()
        
        result = service.update_translation(
            "nonexistent.key",
            "en",
            "Value",
        )
        
        assert result is False
    
    def test_delete_translation(self) -> None:
        """Test deleting a translation."""
        service = I18nBackendService()
        
        service.add_translation(
            key="to_delete",
            namespace=TranslationNamespace.COMMON,
            translations={"en": "Delete me"},
        )
        
        result = service.delete_translation("to_delete")
        
        assert result is True
        assert service.get_translation_key("to_delete") is None
    
    def test_get_translation_key(self) -> None:
        """Test getting translation key object."""
        service = I18nBackendService()
        
        key = service.get_translation_key("common.save")
        
        assert key is not None
        assert isinstance(key, TranslationKey)
        assert key.namespace == TranslationNamespace.COMMON


class TestNamespaces:
    """Tests for translation namespaces."""
    
    def test_get_translations_by_namespace(self) -> None:
        """Test getting all translations in a namespace."""
        service = I18nBackendService()
        
        common = service.get_translations_by_namespace(TranslationNamespace.COMMON)
        
        assert len(common) > 0
        assert "common.save" in common
    
    def test_get_translations_by_namespace_locale(self) -> None:
        """Test getting translations by namespace for specific locale."""
        service = I18nBackendService()
        
        common_fr = service.get_translations_by_namespace(
            TranslationNamespace.COMMON,
            locale="fr",
        )
        
        assert common_fr.get("common.save") == "Enregistrer"
    
    def test_errors_namespace(self) -> None:
        """Test errors namespace."""
        service = I18nBackendService()
        
        errors = service.get_translations_by_namespace(TranslationNamespace.ERRORS)
        
        assert "errors.required" in errors


class TestMissingTranslations:
    """Tests for missing translation tracking."""
    
    def test_missing_translation_recorded(self) -> None:
        """Test that missing translations are recorded."""
        service = I18nBackendService()
        
        # Access missing key
        service.translate("missing.test.key")
        
        missing = service.get_missing_translations()
        
        assert len(missing) > 0
        assert any(m.key == "missing.test.key" for m in missing)
    
    def test_missing_translation_for_locale(self) -> None:
        """Test filtering missing translations by locale."""
        service = I18nBackendService()
        
        service.translate("missing.en.key", locale="en")
        service.translate("missing.fr.key", locale="fr")
        
        missing_fr = service.get_missing_translations(locale="fr")
        
        assert any(m.key == "missing.fr.key" for m in missing_fr)
        assert all(m.locale == "fr" for m in missing_fr)
    
    def test_clear_missing_translations(self) -> None:
        """Test clearing missing translations log."""
        service = I18nBackendService()
        
        service.translate("missing.key1")
        service.translate("missing.key2")
        
        count = service.clear_missing_translations()
        
        assert count >= 2
        assert len(service.get_missing_translations()) == 0
    
    def test_adding_translation_removes_from_missing(self) -> None:
        """Test that adding a translation removes it from missing list."""
        service = I18nBackendService()
        
        service.translate("new.key.to.add")
        
        missing_before = [m for m in service.get_missing_translations() if m.key == "new.key.to.add"]
        assert len(missing_before) > 0
        
        service.add_translation(
            key="new.key.to.add",
            namespace=TranslationNamespace.COMMON,
            translations={"en": "Added"},
        )
        
        missing_after = [m for m in service.get_missing_translations() if m.key == "new.key.to.add"]
        assert len(missing_after) == 0


class TestImportExport:
    """Tests for import/export functionality."""
    
    def test_export_translations(self) -> None:
        """Test exporting translations."""
        service = I18nBackendService()
        
        export = service.export_translations("en")
        
        assert isinstance(export, TranslationExport)
        assert export.locale == "en"
        assert export.key_count > 0
        assert "common.save" in export.translations
    
    def test_export_by_namespace(self) -> None:
        """Test exporting translations for a specific namespace."""
        service = I18nBackendService()
        
        export = service.export_translations("en", namespace=TranslationNamespace.ERRORS)
        
        assert export.namespace == TranslationNamespace.ERRORS
        assert all(k.startswith("errors.") for k in export.translations.keys())
    
    def test_import_translations(self) -> None:
        """Test importing translations."""
        service = I18nBackendService()
        
        translations = {
            "imported.key1": "Value 1",
            "imported.key2": "Value 2",
        }
        
        count = service.import_translations(
            locale="en",
            translations=translations,
        )
        
        assert count == 2
        assert service.translate("imported.key1") == "Value 1"
    
    def test_import_updates_existing(self) -> None:
        """Test that import updates existing translations."""
        service = I18nBackendService()
        
        original = service.translate("common.save")
        
        service.import_translations(
            locale="en",
            translations={"common.save": "Save Updated"},
        )
        
        assert service.translate("common.save") == "Save Updated"


class TestNumberFormatting:
    """Tests for number formatting."""
    
    def test_format_integer(self) -> None:
        """Test formatting an integer."""
        service = I18nBackendService()
        
        result = service.format_number(1000000, "en")
        
        assert result == "1,000,000"
    
    def test_format_float(self) -> None:
        """Test formatting a float."""
        service = I18nBackendService()
        
        result = service.format_number(1234.56, "en")
        
        assert result == "1,234.56"
    
    def test_format_number_french(self) -> None:
        """Test French number formatting."""
        service = I18nBackendService()
        
        result = service.format_number(1234.56, "fr")
        
        # French uses space for thousands and comma for decimal
        assert " " in result  # Thousands separator
        assert "," in result  # Decimal separator
    
    def test_format_number_decimal_places(self) -> None:
        """Test custom decimal places."""
        service = I18nBackendService()
        
        result = service.format_number(123.456789, "en", decimal_places=4)
        
        assert "123.4567" in result or "123.4568" in result


class TestCurrencyFormatting:
    """Tests for currency formatting."""
    
    def test_format_currency_english(self) -> None:
        """Test English currency formatting."""
        service = I18nBackendService()
        
        result = service.format_currency(1234.56, "en")
        
        assert result.startswith("$")
        assert "1,234.56" in result
    
    def test_format_currency_french(self) -> None:
        """Test French currency formatting."""
        service = I18nBackendService()
        
        result = service.format_currency(1234.56, "fr")
        
        # French puts currency after
        assert result.endswith("€")
    
    def test_format_currency_custom_symbol(self) -> None:
        """Test custom currency symbol."""
        service = I18nBackendService()
        
        result = service.format_currency(100, "en", currency_symbol="£")
        
        assert "£" in result


class TestDateFormatting:
    """Tests for date formatting."""
    
    def test_format_date_english(self) -> None:
        """Test English date formatting."""
        service = I18nBackendService()
        
        date = datetime(2024, 3, 15, 14, 30)
        result = service.format_date(date, "en")
        
        # US format: MM/DD/YYYY
        assert "03" in result
        assert "15" in result
        assert "2024" in result
    
    def test_format_date_french(self) -> None:
        """Test French date formatting."""
        service = I18nBackendService()
        
        date = datetime(2024, 3, 15)
        result = service.format_date(date, "fr")
        
        # French format: DD/MM/YYYY
        assert result.startswith("15")
    
    def test_format_time(self) -> None:
        """Test time formatting."""
        service = I18nBackendService()
        
        dt = datetime(2024, 3, 15, 14, 30)
        result = service.format_date(dt, "en", format_type="time")
        
        # Should include time
        assert ":" in result
    
    def test_format_datetime(self) -> None:
        """Test datetime formatting."""
        service = I18nBackendService()
        
        dt = datetime(2024, 3, 15, 14, 30)
        result = service.format_datetime(dt, "en")
        
        # Should include both date and time
        assert "2024" in result
        assert ":" in result
    
    def test_format_relative_time(self) -> None:
        """Test relative time formatting."""
        service = I18nBackendService()
        
        past = datetime.now(timezone.utc) - timedelta(hours=2)
        result = service.format_relative_time(past, "en")
        
        assert "hours" in result or "hour" in result


class TestStatistics:
    """Tests for translation statistics."""
    
    def test_get_statistics(self) -> None:
        """Test getting translation statistics."""
        service = I18nBackendService()
        
        stats = service.get_statistics()
        
        assert "total_keys" in stats
        assert "complete_keys" in stats
        assert "by_namespace" in stats
        assert "by_locale" in stats
        assert stats["total_keys"] > 0
    
    def test_statistics_by_namespace(self) -> None:
        """Test statistics breakdown by namespace."""
        service = I18nBackendService()
        
        stats = service.get_statistics()
        
        assert "common" in stats["by_namespace"]
        assert "errors" in stats["by_namespace"]
    
    def test_statistics_by_locale(self) -> None:
        """Test statistics breakdown by locale."""
        service = I18nBackendService()
        
        stats = service.get_statistics()
        
        assert "en" in stats["by_locale"]
        assert "fr" in stats["by_locale"]


class TestValidation:
    """Tests for translation validation."""
    
    def test_validate_translations(self) -> None:
        """Test validating translations."""
        service = I18nBackendService()
        
        issues = service.validate_translations()
        
        # Should return list of issues
        assert isinstance(issues, list)
    
    def test_validate_missing_locale(self) -> None:
        """Test detecting missing required locales."""
        service = I18nBackendService()
        
        # Add key with only English
        service.add_translation(
            key="incomplete.key",
            namespace=TranslationNamespace.COMMON,
            translations={"en": "English only"},
        )
        
        issues = service.validate_translations()
        
        # Should detect missing French
        locale_issues = [i for i in issues if i["key"] == "incomplete.key" and i["issue"] == "missing_locale"]
        assert len(locale_issues) > 0
    
    def test_validate_placeholder_mismatch(self) -> None:
        """Test detecting placeholder mismatches."""
        service = I18nBackendService()
        
        service.add_translation(
            key="placeholder.test",
            namespace=TranslationNamespace.COMMON,
            translations={
                "en": "Hello {name}, you have {count} items",
                "fr": "Bonjour {name}",  # Missing {count}
            },
        )
        
        issues = service.validate_translations()
        
        mismatch_issues = [i for i in issues if i["key"] == "placeholder.test" and i["issue"] == "placeholder_mismatch"]
        assert len(mismatch_issues) > 0


class TestTranslationKeyProperties:
    """Tests for TranslationKey properties."""
    
    def test_supported_locales(self) -> None:
        """Test getting supported locales for a key."""
        service = I18nBackendService()
        
        key = service.get_translation_key("common.save")
        
        assert "en" in key.supported_locales
        assert "fr" in key.supported_locales
    
    def test_is_complete(self) -> None:
        """Test is_complete property."""
        service = I18nBackendService()
        
        complete_key = service.get_translation_key("common.save")
        assert complete_key.is_complete is True
        
        incomplete = service.add_translation(
            key="incomplete",
            namespace=TranslationNamespace.COMMON,
            translations={"en": "English only"},
        )
        assert incomplete.is_complete is False


class TestEdgeCases:
    """Tests for edge cases."""
    
    def test_translate_empty_variables(self) -> None:
        """Test translation with empty variables dict."""
        service = I18nBackendService()
        
        result = service.translate("common.save", variables={})
        
        assert result == "Save"
    
    def test_translate_none_locale(self) -> None:
        """Test translation with None locale uses default."""
        service = I18nBackendService()
        
        result = service.translate("common.save", locale=None)
        
        assert result == "Save"
    
    def test_format_number_unknown_locale(self) -> None:
        """Test number formatting with unknown locale."""
        service = I18nBackendService()
        
        result = service.format_number(1234, "unknown")
        
        # Should return simple string representation
        assert "1234" in result
    
    def test_duplicate_missing_not_recorded(self) -> None:
        """Test that duplicate missing translations are not recorded."""
        service = I18nBackendService()
        service.clear_missing_translations()
        
        # Access same missing key twice
        service.translate("duplicate.missing")
        service.translate("duplicate.missing")
        
        missing = [m for m in service.get_missing_translations() if m.key == "duplicate.missing"]
        
        assert len(missing) == 1
    
    def test_delete_nonexistent_translation(self) -> None:
        """Test deleting non-existent translation."""
        service = I18nBackendService()
        
        result = service.delete_translation("nonexistent")
        
        assert result is False
