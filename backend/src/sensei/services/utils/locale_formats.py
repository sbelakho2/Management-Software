"""Locale Formats Service.

Configures date, time, number, and currency formats for different locales.
Specifically optimized for Morocco and Tunisia with support for Arabic,
French, and regional formatting conventions.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone, date, time
from decimal import Decimal
from enum import Enum
import logging
from typing import Any, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)


class Locale(Enum):
    """Supported locales."""

    # Primary locales for Morocco/Tunisia
    AR_MA = "ar-MA"  # Arabic (Morocco)
    AR_TN = "ar-TN"  # Arabic (Tunisia)
    FR_MA = "fr-MA"  # French (Morocco)
    FR_TN = "fr-TN"  # French (Tunisia)

    # Additional supported locales
    FR_FR = "fr-FR"  # French (France)
    EN_US = "en-US"  # English (US)
    EN_GB = "en-GB"  # English (UK)


class Currency(Enum):
    """Supported currencies."""

    MAD = "MAD"  # Moroccan Dirham
    TND = "TND"  # Tunisian Dinar
    EUR = "EUR"  # Euro
    USD = "USD"  # US Dollar
    GBP = "GBP"  # British Pound


class DateFormat(Enum):
    """Date format styles."""

    SHORT = "short"  # e.g., 15/01/24
    MEDIUM = "medium"  # e.g., 15 Jan 2024
    LONG = "long"  # e.g., 15 January 2024
    FULL = "full"  # e.g., Monday, 15 January 2024
    ISO = "iso"  # e.g., 2024-01-15


class TimeFormat(Enum):
    """Time format styles."""

    SHORT = "short"  # e.g., 14:30
    MEDIUM = "medium"  # e.g., 14:30:45
    LONG = "long"  # e.g., 14:30:45 UTC
    TWELVE_HOUR = "12h"  # e.g., 2:30 PM


class NumberFormat(Enum):
    """Number format styles."""

    DECIMAL = "decimal"
    PERCENT = "percent"
    SCIENTIFIC = "scientific"


@dataclass
class CurrencyInfo:
    """Currency configuration."""

    code: str  # ISO 4217 code
    symbol: str  # Currency symbol
    name: str  # Full name
    name_ar: str  # Arabic name
    decimal_places: int = 2
    symbol_position: str = "after"  # "before" or "after"


@dataclass
class LocaleConfig:
    """Configuration for a specific locale."""

    locale: Locale
    language: str
    region: str
    date_separator: str = "/"
    time_separator: str = ":"
    decimal_separator: str = ","
    thousands_separator: str = " "
    currency: Currency = Currency.MAD
    default_timezone: str = "Africa/Casablanca"
    first_day_of_week: int = 1  # 0=Sunday, 1=Monday
    calendar_type: str = "gregorian"  # gregorian, hijri
    text_direction: str = "ltr"  # ltr or rtl


@dataclass
class FormattedValue:
    """A formatted value with metadata."""

    raw_value: Any
    formatted: str
    locale: Locale
    format_type: str


@dataclass
class LocaleFormatResult:
    """Result of formatting with locale info."""

    value: str
    locale: str
    format_used: str
    is_rtl: bool = False


# Currency definitions
CURRENCIES: dict[Currency, CurrencyInfo] = {
    Currency.MAD: CurrencyInfo(
        code="MAD",
        symbol="د.م.",
        name="Moroccan Dirham",
        name_ar="درهم مغربي",
        decimal_places=2,
        symbol_position="after",
    ),
    Currency.TND: CurrencyInfo(
        code="TND",
        symbol="د.ت",
        name="Tunisian Dinar",
        name_ar="دينار تونسي",
        decimal_places=3,
        symbol_position="after",
    ),
    Currency.EUR: CurrencyInfo(
        code="EUR",
        symbol="€",
        name="Euro",
        name_ar="يورو",
        decimal_places=2,
        symbol_position="after",
    ),
    Currency.USD: CurrencyInfo(
        code="USD",
        symbol="$",
        name="US Dollar",
        name_ar="دولار أمريكي",
        decimal_places=2,
        symbol_position="before",
    ),
    Currency.GBP: CurrencyInfo(
        code="GBP",
        symbol="£",
        name="British Pound",
        name_ar="جنيه إسترليني",
        decimal_places=2,
        symbol_position="before",
    ),
}

# Locale configurations
LOCALE_CONFIGS: dict[Locale, LocaleConfig] = {
    Locale.AR_MA: LocaleConfig(
        locale=Locale.AR_MA,
        language="ar",
        region="MA",
        date_separator="/",
        decimal_separator=",",
        thousands_separator=" ",
        currency=Currency.MAD,
        default_timezone="Africa/Casablanca",
        first_day_of_week=1,  # Monday
        text_direction="rtl",
    ),
    Locale.AR_TN: LocaleConfig(
        locale=Locale.AR_TN,
        language="ar",
        region="TN",
        date_separator="/",
        decimal_separator=",",
        thousands_separator=" ",
        currency=Currency.TND,
        default_timezone="Africa/Tunis",
        first_day_of_week=1,  # Monday
        text_direction="rtl",
    ),
    Locale.FR_MA: LocaleConfig(
        locale=Locale.FR_MA,
        language="fr",
        region="MA",
        date_separator="/",
        decimal_separator=",",
        thousands_separator=" ",
        currency=Currency.MAD,
        default_timezone="Africa/Casablanca",
        first_day_of_week=1,  # Monday
        text_direction="ltr",
    ),
    Locale.FR_TN: LocaleConfig(
        locale=Locale.FR_TN,
        language="fr",
        region="TN",
        date_separator="/",
        decimal_separator=",",
        thousands_separator=" ",
        currency=Currency.TND,
        default_timezone="Africa/Tunis",
        first_day_of_week=1,  # Monday
        text_direction="ltr",
    ),
    Locale.FR_FR: LocaleConfig(
        locale=Locale.FR_FR,
        language="fr",
        region="FR",
        date_separator="/",
        decimal_separator=",",
        thousands_separator=" ",
        currency=Currency.EUR,
        default_timezone="Europe/Paris",
        first_day_of_week=1,  # Monday
        text_direction="ltr",
    ),
    Locale.EN_US: LocaleConfig(
        locale=Locale.EN_US,
        language="en",
        region="US",
        date_separator="/",
        decimal_separator=".",
        thousands_separator=",",
        currency=Currency.USD,
        default_timezone="America/New_York",
        first_day_of_week=0,  # Sunday
        text_direction="ltr",
    ),
    Locale.EN_GB: LocaleConfig(
        locale=Locale.EN_GB,
        language="en",
        region="GB",
        date_separator="/",
        decimal_separator=".",
        thousands_separator=",",
        currency=Currency.GBP,
        default_timezone="Europe/London",
        first_day_of_week=1,  # Monday
        text_direction="ltr",
    ),
}

# Month names
MONTH_NAMES_FR = [
    "janvier", "février", "mars", "avril", "mai", "juin",
    "juillet", "août", "septembre", "octobre", "novembre", "décembre",
]

MONTH_NAMES_FR_SHORT = [
    "janv.", "févr.", "mars", "avr.", "mai", "juin",
    "juil.", "août", "sept.", "oct.", "nov.", "déc.",
]

MONTH_NAMES_AR = [
    "يناير", "فبراير", "مارس", "أبريل", "مايو", "يونيو",
    "يوليو", "أغسطس", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر",
]

MONTH_NAMES_EN = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]

MONTH_NAMES_EN_SHORT = [
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
]

# Day names
DAY_NAMES_FR = [
    "lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche",
]

DAY_NAMES_AR = [
    "الإثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة", "السبت", "الأحد",
]

DAY_NAMES_EN = [
    "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday",
]


class LocaleFormatsService:
    """Service for locale-aware formatting of dates, times, numbers, and currencies."""

    def __init__(self, default_locale: Locale = Locale.FR_MA) -> None:
        """Initialize the locale formats service."""
        self._default_locale = default_locale
        self._user_locales: dict[str, Locale] = {}

    # --- Locale Management ---

    def get_default_locale(self) -> Locale:
        """Get the default locale."""
        return self._default_locale

    def set_default_locale(self, locale: Locale) -> None:
        """Set the default locale."""
        self._default_locale = locale

    def get_user_locale(self, user_id: str) -> Locale:
        """Get a user's preferred locale."""
        return self._user_locales.get(user_id, self._default_locale)

    def set_user_locale(self, user_id: str, locale: Locale) -> None:
        """Set a user's preferred locale."""
        self._user_locales[user_id] = locale

    def get_locale_config(self, locale: Locale) -> LocaleConfig:
        """Get configuration for a locale."""
        return LOCALE_CONFIGS[locale]

    def get_all_locales(self) -> list[Locale]:
        """Get all supported locales."""
        return list(Locale)

    def get_morocco_locales(self) -> list[Locale]:
        """Get locales for Morocco."""
        return [Locale.AR_MA, Locale.FR_MA]

    def get_tunisia_locales(self) -> list[Locale]:
        """Get locales for Tunisia."""
        return [Locale.AR_TN, Locale.FR_TN]

    # --- Date Formatting ---

    def format_date(
        self,
        value: date | datetime,
        locale: Optional[Locale] = None,
        style: DateFormat = DateFormat.MEDIUM,
    ) -> LocaleFormatResult:
        """Format a date according to locale."""
        loc = locale or self._default_locale
        config = LOCALE_CONFIGS[loc]

        if isinstance(value, datetime):
            d = value.date()
        else:
            d = value

        if style == DateFormat.ISO:
            formatted = d.isoformat()
        elif style == DateFormat.SHORT:
            formatted = f"{d.day:02d}{config.date_separator}{d.month:02d}{config.date_separator}{str(d.year)[2:]}"
        elif style == DateFormat.MEDIUM:
            month_name = self._get_month_name(d.month, loc, short=True)
            formatted = f"{d.day} {month_name} {d.year}"
        elif style == DateFormat.LONG:
            month_name = self._get_month_name(d.month, loc)
            formatted = f"{d.day} {month_name} {d.year}"
        elif style == DateFormat.FULL:
            day_name = self._get_day_name(d.weekday(), loc)
            month_name = self._get_month_name(d.month, loc)
            formatted = f"{day_name}, {d.day} {month_name} {d.year}"
        else:
            formatted = d.isoformat()

        return LocaleFormatResult(
            value=formatted,
            locale=loc.value,
            format_used=style.value,
            is_rtl=config.text_direction == "rtl",
        )

    def _get_month_name(
        self,
        month: int,
        locale: Locale,
        short: bool = False,
    ) -> str:
        """Get month name for locale."""
        idx = month - 1
        if locale.value.startswith("ar"):
            return MONTH_NAMES_AR[idx]
        elif locale.value.startswith("fr"):
            return MONTH_NAMES_FR_SHORT[idx] if short else MONTH_NAMES_FR[idx]
        else:
            return MONTH_NAMES_EN_SHORT[idx] if short else MONTH_NAMES_EN[idx]

    def _get_day_name(self, weekday: int, locale: Locale) -> str:
        """Get day name for locale (weekday is 0=Monday)."""
        if locale.value.startswith("ar"):
            return DAY_NAMES_AR[weekday]
        elif locale.value.startswith("fr"):
            return DAY_NAMES_FR[weekday]
        else:
            return DAY_NAMES_EN[weekday]

    def parse_date(
        self,
        value: str,
        locale: Optional[Locale] = None,
        style: DateFormat = DateFormat.SHORT,
    ) -> Optional[date]:
        """Parse a date string according to locale."""
        loc = locale or self._default_locale
        config = LOCALE_CONFIGS[loc]

        try:
            if style == DateFormat.ISO:
                return date.fromisoformat(value)
            elif style == DateFormat.SHORT:
                parts = value.split(config.date_separator)
                if len(parts) == 3:
                    day, month, year = int(parts[0]), int(parts[1]), int(parts[2])
                    if year < 100:
                        year += 2000
                    return date(year, month, day)
        except (ValueError, IndexError):
            logger.debug("Failed to parse date '%s' for locale %s", value, loc.value)
        return None

    # --- Time Formatting ---

    def format_time(
        self,
        value: time | datetime,
        locale: Optional[Locale] = None,
        style: TimeFormat = TimeFormat.SHORT,
        include_seconds: bool = False,
    ) -> LocaleFormatResult:
        """Format a time according to locale."""
        loc = locale or self._default_locale
        config = LOCALE_CONFIGS[loc]

        if isinstance(value, datetime):
            t = value.time()
        else:
            t = value

        sep = config.time_separator

        if style == TimeFormat.TWELVE_HOUR:
            hour = t.hour % 12
            if hour == 0:
                hour = 12
            period = "PM" if t.hour >= 12 else "AM"
            if include_seconds or style == TimeFormat.MEDIUM:
                formatted = f"{hour}{sep}{t.minute:02d}{sep}{t.second:02d} {period}"
            else:
                formatted = f"{hour}{sep}{t.minute:02d} {period}"
        elif style == TimeFormat.LONG:
            formatted = f"{t.hour:02d}{sep}{t.minute:02d}{sep}{t.second:02d} UTC"
        elif style == TimeFormat.MEDIUM:
            formatted = f"{t.hour:02d}{sep}{t.minute:02d}{sep}{t.second:02d}"
        else:  # SHORT
            formatted = f"{t.hour:02d}{sep}{t.minute:02d}"

        return LocaleFormatResult(
            value=formatted,
            locale=loc.value,
            format_used=style.value,
            is_rtl=config.text_direction == "rtl",
        )

    def format_datetime(
        self,
        value: datetime,
        locale: Optional[Locale] = None,
        date_style: DateFormat = DateFormat.MEDIUM,
        time_style: TimeFormat = TimeFormat.SHORT,
    ) -> LocaleFormatResult:
        """Format a datetime according to locale."""
        date_result = self.format_date(value, locale, date_style)
        time_result = self.format_time(value, locale, time_style)

        formatted = f"{date_result.value} {time_result.value}"

        return LocaleFormatResult(
            value=formatted,
            locale=date_result.locale,
            format_used=f"{date_style.value}+{time_style.value}",
            is_rtl=date_result.is_rtl,
        )

    # --- Number Formatting ---

    def format_number(
        self,
        value: float | int | Decimal,
        locale: Optional[Locale] = None,
        decimal_places: int = 2,
        style: NumberFormat = NumberFormat.DECIMAL,
    ) -> LocaleFormatResult:
        """Format a number according to locale."""
        loc = locale or self._default_locale
        config = LOCALE_CONFIGS[loc]

        if style == NumberFormat.PERCENT:
            value = float(value) * 100
            suffix = " %"
        elif style == NumberFormat.SCIENTIFIC:
            formatted = f"{float(value):.{decimal_places}e}"
            return LocaleFormatResult(
                value=formatted,
                locale=loc.value,
                format_used=style.value,
                is_rtl=config.text_direction == "rtl",
            )
        else:
            suffix = ""

        # Format with decimal places
        num = float(value)
        is_negative = num < 0
        num = abs(num)

        # Split into integer and decimal parts
        int_part = int(num)
        dec_part = round(num - int_part, decimal_places)

        # Format integer part with thousands separator
        int_str = ""
        int_part_str = str(int_part)
        for i, digit in enumerate(reversed(int_part_str)):
            if i > 0 and i % 3 == 0:
                int_str = config.thousands_separator + int_str
            int_str = digit + int_str

        # Format decimal part
        if decimal_places > 0:
            dec_str = f"{dec_part:.{decimal_places}f}"[2:]  # Remove "0."
            formatted = f"{int_str}{config.decimal_separator}{dec_str}"
        else:
            formatted = int_str

        if is_negative:
            formatted = f"-{formatted}"

        formatted += suffix

        return LocaleFormatResult(
            value=formatted,
            locale=loc.value,
            format_used=style.value,
            is_rtl=config.text_direction == "rtl",
        )

    def parse_number(
        self,
        value: str,
        locale: Optional[Locale] = None,
    ) -> Optional[float]:
        """Parse a number string according to locale."""
        loc = locale or self._default_locale
        config = LOCALE_CONFIGS[loc]

        try:
            # Remove thousands separators and replace decimal separator
            cleaned = value.strip()
            cleaned = cleaned.replace(config.thousands_separator, "")
            cleaned = cleaned.replace(config.decimal_separator, ".")
            cleaned = cleaned.replace(" %", "").replace("%", "")
            return float(cleaned)
        except ValueError:
            return None

    # --- Currency Formatting ---

    def get_currency_info(self, currency: Currency) -> CurrencyInfo:
        """Get currency information."""
        return CURRENCIES[currency]

    def get_all_currencies(self) -> list[CurrencyInfo]:
        """Get all supported currencies."""
        return list(CURRENCIES.values())

    def format_currency(
        self,
        value: float | int | Decimal,
        currency: Optional[Currency] = None,
        locale: Optional[Locale] = None,
        decimal_places: Optional[int] = None,
    ) -> LocaleFormatResult:
        """Format a currency value according to locale."""
        loc = locale or self._default_locale
        config = LOCALE_CONFIGS[loc]
        curr = currency or config.currency
        curr_info = CURRENCIES[curr]

        # Use currency's decimal places if not specified
        places = decimal_places if decimal_places is not None else curr_info.decimal_places

        # Format the number
        num_result = self.format_number(value, loc, places)

        # Add currency symbol
        if curr_info.symbol_position == "before":
            formatted = f"{curr_info.symbol}{num_result.value}"
        else:
            formatted = f"{num_result.value} {curr_info.symbol}"

        return LocaleFormatResult(
            value=formatted,
            locale=loc.value,
            format_used=f"currency:{curr.value}",
            is_rtl=config.text_direction == "rtl",
        )

    def format_currency_code(
        self,
        value: float | int | Decimal,
        currency: Optional[Currency] = None,
        locale: Optional[Locale] = None,
    ) -> LocaleFormatResult:
        """Format a currency value with ISO code instead of symbol."""
        loc = locale or self._default_locale
        config = LOCALE_CONFIGS[loc]
        curr = currency or config.currency
        curr_info = CURRENCIES[curr]

        num_result = self.format_number(value, loc, curr_info.decimal_places)

        formatted = f"{num_result.value} {curr.value}"

        return LocaleFormatResult(
            value=formatted,
            locale=loc.value,
            format_used=f"currency_code:{curr.value}",
            is_rtl=config.text_direction == "rtl",
        )

    # --- Relative Time ---

    def format_relative_time(
        self,
        value: datetime,
        reference: Optional[datetime] = None,
        locale: Optional[Locale] = None,
    ) -> LocaleFormatResult:
        """Format relative time (e.g., "2 days ago")."""
        loc = locale or self._default_locale
        config = LOCALE_CONFIGS[loc]

        ref = reference or datetime.now(timezone.utc)

        # Ensure both are aware or both are naive
        if value.tzinfo is None and ref.tzinfo is not None:
            ref = ref.replace(tzinfo=None)
        elif value.tzinfo is not None and ref.tzinfo is None:
            value = value.replace(tzinfo=None)

        diff = ref - value
        seconds = diff.total_seconds()
        is_past = seconds > 0
        seconds = abs(seconds)

        if loc.value.startswith("ar"):
            formatted = self._format_relative_ar(seconds, is_past)
        elif loc.value.startswith("fr"):
            formatted = self._format_relative_fr(seconds, is_past)
        else:
            formatted = self._format_relative_en(seconds, is_past)

        return LocaleFormatResult(
            value=formatted,
            locale=loc.value,
            format_used="relative",
            is_rtl=config.text_direction == "rtl",
        )

    def _format_relative_en(self, seconds: float, is_past: bool) -> str:
        """Format relative time in English."""
        if seconds < 60:
            return "just now" if is_past else "in a moment"
        elif seconds < 3600:
            mins = int(seconds / 60)
            unit = "minute" if mins == 1 else "minutes"
            return f"{mins} {unit} ago" if is_past else f"in {mins} {unit}"
        elif seconds < 86400:
            hours = int(seconds / 3600)
            unit = "hour" if hours == 1 else "hours"
            return f"{hours} {unit} ago" if is_past else f"in {hours} {unit}"
        elif seconds < 604800:
            days = int(seconds / 86400)
            unit = "day" if days == 1 else "days"
            return f"{days} {unit} ago" if is_past else f"in {days} {unit}"
        elif seconds < 2592000:
            weeks = int(seconds / 604800)
            unit = "week" if weeks == 1 else "weeks"
            return f"{weeks} {unit} ago" if is_past else f"in {weeks} {unit}"
        else:
            months = int(seconds / 2592000)
            unit = "month" if months == 1 else "months"
            return f"{months} {unit} ago" if is_past else f"in {months} {unit}"

    def _format_relative_fr(self, seconds: float, is_past: bool) -> str:
        """Format relative time in French."""
        if seconds < 60:
            return "à l'instant" if is_past else "dans un instant"
        elif seconds < 3600:
            mins = int(seconds / 60)
            unit = "minute" if mins == 1 else "minutes"
            return f"il y a {mins} {unit}" if is_past else f"dans {mins} {unit}"
        elif seconds < 86400:
            hours = int(seconds / 3600)
            unit = "heure" if hours == 1 else "heures"
            return f"il y a {hours} {unit}" if is_past else f"dans {hours} {unit}"
        elif seconds < 604800:
            days = int(seconds / 86400)
            unit = "jour" if days == 1 else "jours"
            return f"il y a {days} {unit}" if is_past else f"dans {days} {unit}"
        elif seconds < 2592000:
            weeks = int(seconds / 604800)
            unit = "semaine" if weeks == 1 else "semaines"
            return f"il y a {weeks} {unit}" if is_past else f"dans {weeks} {unit}"
        else:
            months = int(seconds / 2592000)
            return f"il y a {months} mois" if is_past else f"dans {months} mois"

    def _format_relative_ar(self, seconds: float, is_past: bool) -> str:
        """Format relative time in Arabic."""
        if seconds < 60:
            return "الآن" if is_past else "بعد قليل"
        elif seconds < 3600:
            mins = int(seconds / 60)
            return f"منذ {mins} دقيقة" if is_past else f"بعد {mins} دقيقة"
        elif seconds < 86400:
            hours = int(seconds / 3600)
            return f"منذ {hours} ساعة" if is_past else f"بعد {hours} ساعة"
        elif seconds < 604800:
            days = int(seconds / 86400)
            return f"منذ {days} يوم" if is_past else f"بعد {days} يوم"
        elif seconds < 2592000:
            weeks = int(seconds / 604800)
            return f"منذ {weeks} أسبوع" if is_past else f"بعد {weeks} أسبوع"
        else:
            months = int(seconds / 2592000)
            return f"منذ {months} شهر" if is_past else f"بعد {months} شهر"

    # --- Duration Formatting ---

    def format_duration(
        self,
        seconds: float | int,
        locale: Optional[Locale] = None,
        include_seconds: bool = True,
    ) -> LocaleFormatResult:
        """Format a duration in human-readable form."""
        loc = locale or self._default_locale
        config = LOCALE_CONFIGS[loc]

        hours, remainder = divmod(int(seconds), 3600)
        minutes, secs = divmod(remainder, 60)

        if loc.value.startswith("ar"):
            formatted = self._format_duration_ar(hours, minutes, secs, include_seconds)
        elif loc.value.startswith("fr"):
            formatted = self._format_duration_fr(hours, minutes, secs, include_seconds)
        else:
            formatted = self._format_duration_en(hours, minutes, secs, include_seconds)

        return LocaleFormatResult(
            value=formatted,
            locale=loc.value,
            format_used="duration",
            is_rtl=config.text_direction == "rtl",
        )

    def _format_duration_en(
        self,
        hours: int,
        minutes: int,
        seconds: int,
        include_seconds: bool,
    ) -> str:
        """Format duration in English."""
        parts = []
        if hours > 0:
            parts.append(f"{hours}h")
        if minutes > 0 or hours > 0:
            parts.append(f"{minutes}m")
        if include_seconds and (seconds > 0 or (hours == 0 and minutes == 0)):
            parts.append(f"{seconds}s")
        return " ".join(parts) or "0s"

    def _format_duration_fr(
        self,
        hours: int,
        minutes: int,
        seconds: int,
        include_seconds: bool,
    ) -> str:
        """Format duration in French."""
        parts = []
        if hours > 0:
            parts.append(f"{hours}h")
        if minutes > 0 or hours > 0:
            parts.append(f"{minutes}min")
        if include_seconds and (seconds > 0 or (hours == 0 and minutes == 0)):
            parts.append(f"{seconds}s")
        return " ".join(parts) or "0s"

    def _format_duration_ar(
        self,
        hours: int,
        minutes: int,
        seconds: int,
        include_seconds: bool,
    ) -> str:
        """Format duration in Arabic."""
        parts = []
        if hours > 0:
            parts.append(f"{hours}س")
        if minutes > 0 or hours > 0:
            parts.append(f"{minutes}د")
        if include_seconds and (seconds > 0 or (hours == 0 and minutes == 0)):
            parts.append(f"{seconds}ث")
        return " ".join(parts) or "0ث"

    # --- Utility Methods ---

    def get_timezone_for_locale(self, locale: Optional[Locale] = None) -> str:
        """Get the default timezone for a locale."""
        loc = locale or self._default_locale
        return LOCALE_CONFIGS[loc].default_timezone

    def get_first_day_of_week(self, locale: Optional[Locale] = None) -> int:
        """Get the first day of week for a locale (0=Sunday, 1=Monday)."""
        loc = locale or self._default_locale
        return LOCALE_CONFIGS[loc].first_day_of_week

    def is_rtl(self, locale: Optional[Locale] = None) -> bool:
        """Check if locale is right-to-left."""
        loc = locale or self._default_locale
        return LOCALE_CONFIGS[loc].text_direction == "rtl"

    def get_language(self, locale: Optional[Locale] = None) -> str:
        """Get the language code for a locale."""
        loc = locale or self._default_locale
        return LOCALE_CONFIGS[loc].language

    def get_region(self, locale: Optional[Locale] = None) -> str:
        """Get the region code for a locale."""
        loc = locale or self._default_locale
        return LOCALE_CONFIGS[loc].region
