"""
Internationalization (i18n) Backend Service.

Provides backend support for multi-language capabilities including
translation management, locale handling, and content localization.

Features:
- Translation key-value management
- Multiple locale support (English, French, etc.)
- Fallback locale handling
- Interpolation/variable substitution
- Pluralization rules
- Date/time/number formatting
- Translation export/import
- Missing translation tracking
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import logging
from typing import Any, Callable
from uuid import UUID, uuid4

logger = logging.getLogger(__name__)


class Locale(str, Enum):
    """Supported locales."""
    
    EN = "en"  # English (default)
    FR = "fr"  # French
    AR = "ar"  # Arabic
    ES = "es"  # Spanish
    DE = "de"  # German
    PT = "pt"  # Portuguese
    ZH = "zh"  # Chinese
    JA = "ja"  # Japanese


class TranslationNamespace(str, Enum):
    """Namespaces for organizing translations."""
    
    COMMON = "common"
    ERRORS = "errors"
    VALIDATION = "validation"
    NOTIFICATIONS = "notifications"
    EMAILS = "emails"
    LABELS = "labels"
    BUTTONS = "buttons"
    MESSAGES = "messages"
    ENTITIES = "entities"
    STATUSES = "statuses"
    REPORTS = "reports"


class PluralCategory(str, Enum):
    """Plural categories for different languages."""
    
    ZERO = "zero"
    ONE = "one"
    TWO = "two"
    FEW = "few"
    MANY = "many"
    OTHER = "other"


@dataclass
class TranslationKey:
    """A translation key with its value in multiple locales."""
    
    id: UUID
    key: str
    namespace: TranslationNamespace
    translations: dict[str, str]  # locale -> translation
    plural_translations: dict[str, dict[str, str]] | None = None  # locale -> category -> translation
    description: str | None = None
    context: str | None = None  # Additional context for translators
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: UUID | None = None
    
    def get_translation(self, locale: str) -> str | None:
        """Get translation for a locale."""
        return self.translations.get(locale)
    
    def get_plural_translation(self, locale: str, category: str) -> str | None:
        """Get plural translation for a locale and category."""
        if self.plural_translations and locale in self.plural_translations:
            return self.plural_translations[locale].get(category)
        return None
    
    @property
    def supported_locales(self) -> list[str]:
        """Get list of locales that have translations."""
        return list(self.translations.keys())
    
    @property
    def is_complete(self) -> bool:
        """Check if all required locales have translations."""
        required = [Locale.EN.value, Locale.FR.value]
        return all(loc in self.translations for loc in required)


@dataclass
class MissingTranslation:
    """Record of a missing translation."""
    
    id: UUID
    key: str
    namespace: TranslationNamespace
    locale: str
    detected_at: datetime
    context: str | None = None
    reported_by: UUID | None = None


@dataclass
class LocaleConfig:
    """Configuration for a locale."""
    
    code: str
    name: str
    native_name: str
    direction: str = "ltr"  # ltr or rtl
    date_format: str = "YYYY-MM-DD"
    time_format: str = "HH:mm"
    datetime_format: str = "YYYY-MM-DD HH:mm"
    number_decimal: str = "."
    number_thousands: str = ","
    currency_symbol: str = "$"
    currency_position: str = "before"  # before or after
    first_day_of_week: int = 0  # 0 = Sunday, 1 = Monday
    enabled: bool = True


@dataclass
class TranslationExport:
    """Export of translations for a locale."""
    
    locale: str
    namespace: TranslationNamespace | None
    translations: dict[str, str]
    exported_at: datetime
    key_count: int


class I18nBackendService:
    """Service for internationalization support."""
    
    def __init__(
        self,
        default_locale: str = "en",
        fallback_locale: str = "en",
    ) -> None:
        """Initialize the service."""
        self._translations: dict[str, TranslationKey] = {}  # key -> TranslationKey
        self._missing_translations: dict[UUID, MissingTranslation] = {}
        self._locale_configs: dict[str, LocaleConfig] = {}
        self._default_locale = default_locale
        self._fallback_locale = fallback_locale
        self._custom_formatters: dict[str, Callable[[Any, str], str]] = {}
        
        # Initialize default locale configs
        self._initialize_locale_configs()
        
        # Initialize default translations
        self._initialize_default_translations()
    
    def _initialize_locale_configs(self) -> None:
        """Set up default locale configurations."""
        self._locale_configs = {
            "en": LocaleConfig(
                code="en",
                name="English",
                native_name="English",
                direction="ltr",
                date_format="MM/DD/YYYY",
                time_format="h:mm A",
                datetime_format="MM/DD/YYYY h:mm A",
                number_decimal=".",
                number_thousands=",",
                currency_symbol="$",
                currency_position="before",
                first_day_of_week=0,
            ),
            "fr": LocaleConfig(
                code="fr",
                name="French",
                native_name="Français",
                direction="ltr",
                date_format="DD/MM/YYYY",
                time_format="HH:mm",
                datetime_format="DD/MM/YYYY HH:mm",
                number_decimal=",",
                number_thousands=" ",
                currency_symbol="€",
                currency_position="after",
                first_day_of_week=1,
            ),
            "ar": LocaleConfig(
                code="ar",
                name="Arabic",
                native_name="العربية",
                direction="rtl",
                date_format="DD/MM/YYYY",
                time_format="HH:mm",
                datetime_format="DD/MM/YYYY HH:mm",
                number_decimal="٫",
                number_thousands="٬",
                currency_symbol="د.م.",
                currency_position="after",
                first_day_of_week=6,
            ),
            "es": LocaleConfig(
                code="es",
                name="Spanish",
                native_name="Español",
                direction="ltr",
                date_format="DD/MM/YYYY",
                time_format="HH:mm",
                datetime_format="DD/MM/YYYY HH:mm",
                number_decimal=",",
                number_thousands=".",
                currency_symbol="€",
                currency_position="after",
                first_day_of_week=1,
            ),
            "de": LocaleConfig(
                code="de",
                name="German",
                native_name="Deutsch",
                direction="ltr",
                date_format="DD.MM.YYYY",
                time_format="HH:mm",
                datetime_format="DD.MM.YYYY HH:mm",
                number_decimal=",",
                number_thousands=".",
                currency_symbol="€",
                currency_position="after",
                first_day_of_week=1,
            ),
        }
    
    def _initialize_default_translations(self) -> None:
        """Set up default translations."""
        defaults = [
            # Common
            ("common.save", TranslationNamespace.COMMON, {"en": "Save", "fr": "Enregistrer"}),
            ("common.cancel", TranslationNamespace.COMMON, {"en": "Cancel", "fr": "Annuler"}),
            ("common.delete", TranslationNamespace.COMMON, {"en": "Delete", "fr": "Supprimer"}),
            ("common.edit", TranslationNamespace.COMMON, {"en": "Edit", "fr": "Modifier"}),
            ("common.create", TranslationNamespace.COMMON, {"en": "Create", "fr": "Créer"}),
            ("common.search", TranslationNamespace.COMMON, {"en": "Search", "fr": "Rechercher"}),
            ("common.loading", TranslationNamespace.COMMON, {"en": "Loading...", "fr": "Chargement..."}),
            ("common.confirm", TranslationNamespace.COMMON, {"en": "Confirm", "fr": "Confirmer"}),
            ("common.back", TranslationNamespace.COMMON, {"en": "Back", "fr": "Retour"}),
            ("common.next", TranslationNamespace.COMMON, {"en": "Next", "fr": "Suivant"}),
            ("common.previous", TranslationNamespace.COMMON, {"en": "Previous", "fr": "Précédent"}),
            ("common.yes", TranslationNamespace.COMMON, {"en": "Yes", "fr": "Oui"}),
            ("common.no", TranslationNamespace.COMMON, {"en": "No", "fr": "Non"}),
            
            # Errors
            ("errors.required", TranslationNamespace.ERRORS, {"en": "This field is required", "fr": "Ce champ est obligatoire"}),
            ("errors.invalid_email", TranslationNamespace.ERRORS, {"en": "Invalid email address", "fr": "Adresse e-mail invalide"}),
            ("errors.not_found", TranslationNamespace.ERRORS, {"en": "Not found", "fr": "Non trouvé"}),
            ("errors.unauthorized", TranslationNamespace.ERRORS, {"en": "Unauthorized", "fr": "Non autorisé"}),
            ("errors.forbidden", TranslationNamespace.ERRORS, {"en": "Access denied", "fr": "Accès refusé"}),
            ("errors.server_error", TranslationNamespace.ERRORS, {"en": "Server error", "fr": "Erreur serveur"}),
            ("errors.validation_failed", TranslationNamespace.ERRORS, {"en": "Validation failed", "fr": "Échec de la validation"}),
            
            # Entities
            ("entities.opportunity", TranslationNamespace.ENTITIES, {"en": "Opportunity", "fr": "Opportunité"}),
            ("entities.rfq", TranslationNamespace.ENTITIES, {"en": "RFQ", "fr": "Appel d'offres"}),
            ("entities.quote", TranslationNamespace.ENTITIES, {"en": "Quote", "fr": "Devis"}),
            ("entities.task", TranslationNamespace.ENTITIES, {"en": "Task", "fr": "Tâche"}),
            ("entities.account", TranslationNamespace.ENTITIES, {"en": "Account", "fr": "Compte"}),
            ("entities.contact", TranslationNamespace.ENTITIES, {"en": "Contact", "fr": "Contact"}),
            ("entities.user", TranslationNamespace.ENTITIES, {"en": "User", "fr": "Utilisateur"}),
            ("entities.work_order", TranslationNamespace.ENTITIES, {"en": "Work Order", "fr": "Ordre de travail"}),
            
            # Statuses
            ("statuses.draft", TranslationNamespace.STATUSES, {"en": "Draft", "fr": "Brouillon"}),
            ("statuses.pending", TranslationNamespace.STATUSES, {"en": "Pending", "fr": "En attente"}),
            ("statuses.approved", TranslationNamespace.STATUSES, {"en": "Approved", "fr": "Approuvé"}),
            ("statuses.rejected", TranslationNamespace.STATUSES, {"en": "Rejected", "fr": "Rejeté"}),
            ("statuses.completed", TranslationNamespace.STATUSES, {"en": "Completed", "fr": "Terminé"}),
            ("statuses.cancelled", TranslationNamespace.STATUSES, {"en": "Cancelled", "fr": "Annulé"}),
            ("statuses.active", TranslationNamespace.STATUSES, {"en": "Active", "fr": "Actif"}),
            ("statuses.inactive", TranslationNamespace.STATUSES, {"en": "Inactive", "fr": "Inactif"}),
            
            # Messages
            ("messages.saved_successfully", TranslationNamespace.MESSAGES, {"en": "Saved successfully", "fr": "Enregistré avec succès"}),
            ("messages.deleted_successfully", TranslationNamespace.MESSAGES, {"en": "Deleted successfully", "fr": "Supprimé avec succès"}),
            ("messages.confirm_delete", TranslationNamespace.MESSAGES, {"en": "Are you sure you want to delete this?", "fr": "Êtes-vous sûr de vouloir supprimer ceci ?"}),
            ("messages.no_results", TranslationNamespace.MESSAGES, {"en": "No results found", "fr": "Aucun résultat trouvé"}),
            
            # Notifications
            ("notifications.task_assigned", TranslationNamespace.NOTIFICATIONS, {"en": "You have been assigned a task", "fr": "Une tâche vous a été attribuée"}),
            ("notifications.task_due", TranslationNamespace.NOTIFICATIONS, {"en": "Task is due today", "fr": "La tâche est due aujourd'hui"}),
            ("notifications.approval_required", TranslationNamespace.NOTIFICATIONS, {"en": "Approval required", "fr": "Approbation requise"}),
        ]
        
        for key, namespace, translations in defaults:
            self._translations[key] = TranslationKey(
                id=uuid4(),
                key=key,
                namespace=namespace,
                translations=translations,
            )
    
    def get_locale_config(self, locale: str) -> LocaleConfig | None:
        """Get configuration for a locale."""
        return self._locale_configs.get(locale)
    
    def get_supported_locales(self) -> list[LocaleConfig]:
        """Get all supported locales."""
        return [c for c in self._locale_configs.values() if c.enabled]
    
    def set_locale_enabled(self, locale: str, enabled: bool) -> bool:
        """Enable or disable a locale."""
        config = self._locale_configs.get(locale)
        if config:
            config.enabled = enabled
            return True
        return False
    
    def translate(
        self,
        key: str,
        locale: str | None = None,
        default: str | None = None,
        variables: dict[str, Any] | None = None,
        count: int | None = None,
    ) -> str:
        """
        Translate a key to the specified locale.
        
        Args:
            key: The translation key
            locale: Target locale (uses default if not specified)
            default: Default value if translation not found
            variables: Variables for interpolation
            count: Count for pluralization
        
        Returns:
            Translated string
        """
        locale = locale or self._default_locale
        trans_key = self._translations.get(key)
        
        if not trans_key:
            self._record_missing(key, locale)
            return default or key
        
        # Handle pluralization
        if count is not None and trans_key.plural_translations:
            category = self._get_plural_category(locale, count)
            translation = trans_key.get_plural_translation(locale, category)
            if translation is None:
                translation = trans_key.get_plural_translation(self._fallback_locale, category)
        else:
            translation = trans_key.get_translation(locale)
            if translation is None:
                translation = trans_key.get_translation(self._fallback_locale)
        
        if translation is None:
            self._record_missing(key, locale)
            return default or key
        
        # Handle interpolation
        if variables:
            translation = self._interpolate(translation, variables, locale)
        
        if count is not None:
            translation = translation.replace("{count}", str(count))
        
        return translation
    
    def t(
        self,
        key: str,
        locale: str | None = None,
        **kwargs: Any,
    ) -> str:
        """Shorthand for translate."""
        variables = {k: v for k, v in kwargs.items() if k not in ("default", "count")}
        return self.translate(
            key,
            locale,
            default=kwargs.get("default"),
            variables=variables if variables else None,
            count=kwargs.get("count"),
        )
    
    def _interpolate(
        self,
        text: str,
        variables: dict[str, Any],
        locale: str,
    ) -> str:
        """Substitute variables in a translation."""
        result = text
        for var_name, var_value in variables.items():
            placeholder = "{" + var_name + "}"
            
            # Format value based on type
            if isinstance(var_value, (int, float)):
                formatted = self.format_number(var_value, locale)
            elif isinstance(var_value, datetime):
                formatted = self.format_datetime(var_value, locale)
            else:
                formatted = str(var_value)
            
            result = result.replace(placeholder, formatted)
        
        return result
    
    def _get_plural_category(self, locale: str, count: int) -> str:
        """Get plural category for a count in a locale."""
        # Simplified plural rules
        if locale in ("en", "de", "es", "pt"):
            # Germanic/Romance languages
            return "one" if count == 1 else "other"
        elif locale == "fr":
            # French: 0 and 1 are singular
            return "one" if count in (0, 1) else "other"
        elif locale == "ar":
            # Arabic has complex plural rules
            if count == 0:
                return "zero"
            elif count == 1:
                return "one"
            elif count == 2:
                return "two"
            elif 3 <= count % 100 <= 10:
                return "few"
            elif 11 <= count % 100 <= 99:
                return "many"
            else:
                return "other"
        else:
            return "other"
    
    def _record_missing(
        self,
        key: str,
        locale: str,
        context: str | None = None,
    ) -> None:
        """Record a missing translation."""
        # Check if already recorded
        for missing in self._missing_translations.values():
            if missing.key == key and missing.locale == locale:
                return
        
        namespace = TranslationNamespace.COMMON
        if "." in key:
            ns_part = key.split(".")[0]
            try:
                namespace = TranslationNamespace(ns_part)
            except ValueError:
                logger.debug("Unknown translation namespace: %s", ns_part)
        
        missing = MissingTranslation(
            id=uuid4(),
            key=key,
            namespace=namespace,
            locale=locale,
            detected_at=datetime.now(timezone.utc),
            context=context,
        )
        self._missing_translations[missing.id] = missing
    
    def add_translation(
        self,
        key: str,
        namespace: TranslationNamespace,
        translations: dict[str, str],
        description: str | None = None,
        context: str | None = None,
        created_by: UUID | None = None,
    ) -> TranslationKey:
        """Add a new translation key."""
        trans_key = TranslationKey(
            id=uuid4(),
            key=key,
            namespace=namespace,
            translations=translations,
            description=description,
            context=context,
            created_by=created_by,
        )
        self._translations[key] = trans_key
        
        # Remove from missing if it exists
        to_remove = []
        for missing_id, missing in self._missing_translations.items():
            if missing.key == key:
                to_remove.append(missing_id)
        for mid in to_remove:
            del self._missing_translations[mid]
        
        return trans_key
    
    def add_plural_translation(
        self,
        key: str,
        locale: str,
        translations: dict[str, str],
    ) -> bool:
        """Add plural translations for a key."""
        trans_key = self._translations.get(key)
        if not trans_key:
            return False
        
        if trans_key.plural_translations is None:
            trans_key.plural_translations = {}
        
        trans_key.plural_translations[locale] = translations
        trans_key.updated_at = datetime.now(timezone.utc)
        return True
    
    def update_translation(
        self,
        key: str,
        locale: str,
        value: str,
    ) -> bool:
        """Update a translation for a specific locale."""
        trans_key = self._translations.get(key)
        if not trans_key:
            return False
        
        trans_key.translations[locale] = value
        trans_key.updated_at = datetime.now(timezone.utc)
        return True
    
    def delete_translation(self, key: str) -> bool:
        """Delete a translation key."""
        if key in self._translations:
            del self._translations[key]
            return True
        return False
    
    def get_translation_key(self, key: str) -> TranslationKey | None:
        """Get a translation key object."""
        return self._translations.get(key)
    
    def get_translations_by_namespace(
        self,
        namespace: TranslationNamespace,
        locale: str | None = None,
    ) -> dict[str, str]:
        """Get all translations in a namespace."""
        locale = locale or self._default_locale
        result: dict[str, str] = {}
        
        for trans_key in self._translations.values():
            if trans_key.namespace == namespace:
                translation = trans_key.get_translation(locale)
                if translation:
                    result[trans_key.key] = translation
        
        return result
    
    def get_missing_translations(
        self,
        locale: str | None = None,
    ) -> list[MissingTranslation]:
        """Get list of missing translations."""
        missing = list(self._missing_translations.values())
        if locale:
            missing = [m for m in missing if m.locale == locale]
        return sorted(missing, key=lambda m: m.detected_at, reverse=True)
    
    def export_translations(
        self,
        locale: str,
        namespace: TranslationNamespace | None = None,
    ) -> TranslationExport:
        """Export translations for a locale."""
        translations: dict[str, str] = {}
        
        for trans_key in self._translations.values():
            if namespace and trans_key.namespace != namespace:
                continue
            
            translation = trans_key.get_translation(locale)
            if translation:
                translations[trans_key.key] = translation
        
        return TranslationExport(
            locale=locale,
            namespace=namespace,
            translations=translations,
            exported_at=datetime.now(timezone.utc),
            key_count=len(translations),
        )
    
    def import_translations(
        self,
        locale: str,
        translations: dict[str, str],
        namespace: TranslationNamespace = TranslationNamespace.COMMON,
        created_by: UUID | None = None,
    ) -> int:
        """Import translations for a locale."""
        imported_count = 0
        
        for key, value in translations.items():
            if key in self._translations:
                # Update existing
                self._translations[key].translations[locale] = value
                self._translations[key].updated_at = datetime.now(timezone.utc)
            else:
                # Create new
                self.add_translation(
                    key=key,
                    namespace=namespace,
                    translations={locale: value},
                    created_by=created_by,
                )
            imported_count += 1
        
        return imported_count
    
    def format_number(
        self,
        value: int | float,
        locale: str | None = None,
        decimal_places: int = 2,
    ) -> str:
        """Format a number according to locale."""
        locale = locale or self._default_locale
        config = self._locale_configs.get(locale)
        
        if config is None:
            return str(value)
        
        # Format with decimal places
        if isinstance(value, float):
            formatted = f"{value:,.{decimal_places}f}"
        else:
            formatted = f"{value:,}"
        
        # Replace separators
        formatted = formatted.replace(",", "THOUSANDS").replace(".", "DECIMAL")
        formatted = formatted.replace("THOUSANDS", config.number_thousands)
        formatted = formatted.replace("DECIMAL", config.number_decimal)
        
        return formatted
    
    def format_currency(
        self,
        value: float,
        locale: str | None = None,
        currency_symbol: str | None = None,
    ) -> str:
        """Format a currency value according to locale."""
        locale = locale or self._default_locale
        config = self._locale_configs.get(locale)
        
        if config is None:
            return f"${value:.2f}"
        
        symbol = currency_symbol or config.currency_symbol
        number = self.format_number(value, locale, decimal_places=2)
        
        if config.currency_position == "before":
            return f"{symbol}{number}"
        else:
            return f"{number} {symbol}"
    
    def format_date(
        self,
        value: datetime,
        locale: str | None = None,
        format_type: str = "date",  # date, time, datetime
    ) -> str:
        """Format a date according to locale."""
        locale = locale or self._default_locale
        config = self._locale_configs.get(locale)
        
        if config is None:
            return value.strftime("%Y-%m-%d")
        
        if format_type == "time":
            fmt = config.time_format
        elif format_type == "datetime":
            fmt = config.datetime_format
        else:
            fmt = config.date_format
        
        # Simple format conversion
        result = fmt
        result = result.replace("YYYY", value.strftime("%Y"))
        result = result.replace("MM", value.strftime("%m"))
        result = result.replace("DD", value.strftime("%d"))
        result = result.replace("HH", value.strftime("%H"))
        result = result.replace("mm", value.strftime("%M"))
        result = result.replace("h", value.strftime("%I").lstrip("0"))
        result = result.replace("A", value.strftime("%p"))
        
        return result
    
    def format_datetime(
        self,
        value: datetime,
        locale: str | None = None,
    ) -> str:
        """Format a datetime according to locale."""
        return self.format_date(value, locale, format_type="datetime")
    
    def format_relative_time(
        self,
        value: datetime,
        locale: str | None = None,
    ) -> str:
        """Format relative time (e.g., '2 hours ago')."""
        locale = locale or self._default_locale
        now = datetime.now(timezone.utc)
        
        # Make both aware or both naive
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        
        diff = now - value
        seconds = int(diff.total_seconds())
        
        if seconds < 0:
            # Future
            seconds = abs(seconds)
            suffix = self.t("common.from_now", locale, default="from now")
        else:
            suffix = self.t("common.ago", locale, default="ago")
        
        if seconds < 60:
            return self.t("common.just_now", locale, default="just now")
        elif seconds < 3600:
            minutes = seconds // 60
            unit = self.t("common.minutes", locale, default="minutes", count=minutes)
            return f"{minutes} {unit} {suffix}"
        elif seconds < 86400:
            hours = seconds // 3600
            unit = self.t("common.hours", locale, default="hours", count=hours)
            return f"{hours} {unit} {suffix}"
        else:
            days = seconds // 86400
            unit = self.t("common.days", locale, default="days", count=days)
            return f"{days} {unit} {suffix}"
    
    def get_statistics(self) -> dict[str, Any]:
        """Get translation statistics."""
        total_keys = len(self._translations)
        by_namespace: dict[str, int] = {}
        by_locale: dict[str, int] = {}
        complete_keys = 0
        
        for trans_key in self._translations.values():
            ns = trans_key.namespace.value
            by_namespace[ns] = by_namespace.get(ns, 0) + 1
            
            for locale in trans_key.supported_locales:
                by_locale[locale] = by_locale.get(locale, 0) + 1
            
            if trans_key.is_complete:
                complete_keys += 1
        
        return {
            "total_keys": total_keys,
            "complete_keys": complete_keys,
            "completion_rate": (complete_keys / total_keys * 100) if total_keys > 0 else 100,
            "by_namespace": by_namespace,
            "by_locale": by_locale,
            "missing_count": len(self._missing_translations),
        }
    
    def validate_translations(self) -> list[dict[str, Any]]:
        """Validate all translations for issues."""
        issues: list[dict[str, Any]] = []
        
        for trans_key in self._translations.values():
            # Check for missing required locales
            for locale in [Locale.EN.value, Locale.FR.value]:
                if locale not in trans_key.translations:
                    issues.append({
                        "key": trans_key.key,
                        "issue": "missing_locale",
                        "locale": locale,
                    })
            
            # Check for placeholder mismatches
            en_translation = trans_key.translations.get("en", "")
            en_placeholders = self._extract_placeholders(en_translation)
            
            for locale, translation in trans_key.translations.items():
                if locale == "en":
                    continue
                locale_placeholders = self._extract_placeholders(translation)
                if en_placeholders != locale_placeholders:
                    issues.append({
                        "key": trans_key.key,
                        "issue": "placeholder_mismatch",
                        "locale": locale,
                        "expected": list(en_placeholders),
                        "found": list(locale_placeholders),
                    })
        
        return issues
    
    def _extract_placeholders(self, text: str) -> set[str]:
        """Extract placeholder names from a translation."""
        import re
        return set(re.findall(r"\{(\w+)\}", text))
    
    def clear_missing_translations(self) -> int:
        """Clear the missing translations log."""
        count = len(self._missing_translations)
        self._missing_translations.clear()
        return count
