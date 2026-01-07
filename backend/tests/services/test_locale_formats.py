"""Tests for Locale Formats Service.

Tests date, time, number, and currency formatting for Morocco/Tunisia locales.
"""

import pytest
from datetime import datetime, timezone, date, time, timedelta
from decimal import Decimal

from sensei.services.locale_formats import (
    LocaleFormatsService,
    LocaleConfig,
    LocaleFormatResult,
    FormattedValue,
    CurrencyInfo,
    Locale,
    Currency,
    DateFormat,
    TimeFormat,
    NumberFormat,
    CURRENCIES,
    LOCALE_CONFIGS,
    MONTH_NAMES_FR,
    MONTH_NAMES_AR,
    MONTH_NAMES_EN,
    DAY_NAMES_FR,
    DAY_NAMES_AR,
    DAY_NAMES_EN,
)


# ============================================================
# Fixtures
# ============================================================


@pytest.fixture
def service() -> LocaleFormatsService:
    """Create a fresh LocaleFormatsService instance."""
    return LocaleFormatsService()


@pytest.fixture
def sample_date() -> date:
    """Create a sample date for testing."""
    return date(2024, 1, 15)


@pytest.fixture
def sample_datetime() -> datetime:
    """Create a sample datetime for testing."""
    return datetime(2024, 1, 15, 14, 30, 45, tzinfo=timezone.utc)


@pytest.fixture
def sample_time() -> time:
    """Create a sample time for testing."""
    return time(14, 30, 45)


# ============================================================
# Enum Tests
# ============================================================


class TestEnums:
    """Test enum values."""

    def test_locales_complete(self) -> None:
        """Verify all expected locales exist."""
        expected = {"ar-MA", "ar-TN", "fr-MA", "fr-TN", "fr-FR", "en-US", "en-GB"}
        actual = {loc.value for loc in Locale}
        assert actual == expected

    def test_currencies_complete(self) -> None:
        """Verify all expected currencies exist."""
        expected = {"MAD", "TND", "EUR", "USD", "GBP"}
        actual = {curr.value for curr in Currency}
        assert actual == expected

    def test_date_formats_complete(self) -> None:
        """Verify all date formats exist."""
        expected = {"short", "medium", "long", "full", "iso"}
        actual = {fmt.value for fmt in DateFormat}
        assert actual == expected

    def test_time_formats_complete(self) -> None:
        """Verify all time formats exist."""
        expected = {"short", "medium", "long", "12h"}
        actual = {fmt.value for fmt in TimeFormat}
        assert actual == expected


# ============================================================
# Currency Info Tests
# ============================================================


class TestCurrencyInfo:
    """Test currency information."""

    def test_moroccan_dirham(self) -> None:
        """Test MAD currency info."""
        mad = CURRENCIES[Currency.MAD]
        assert mad.code == "MAD"
        assert mad.symbol == "د.م."
        assert mad.name == "Moroccan Dirham"
        assert mad.name_ar == "درهم مغربي"
        assert mad.decimal_places == 2
        assert mad.symbol_position == "after"

    def test_tunisian_dinar(self) -> None:
        """Test TND currency info."""
        tnd = CURRENCIES[Currency.TND]
        assert tnd.code == "TND"
        assert tnd.symbol == "د.ت"
        assert tnd.name == "Tunisian Dinar"
        assert tnd.decimal_places == 3  # TND has 3 decimal places

    def test_euro(self) -> None:
        """Test EUR currency info."""
        eur = CURRENCIES[Currency.EUR]
        assert eur.code == "EUR"
        assert eur.symbol == "€"
        assert eur.decimal_places == 2

    def test_usd(self) -> None:
        """Test USD currency info."""
        usd = CURRENCIES[Currency.USD]
        assert usd.code == "USD"
        assert usd.symbol == "$"
        assert usd.symbol_position == "before"


# ============================================================
# Locale Config Tests
# ============================================================


class TestLocaleConfig:
    """Test locale configurations."""

    def test_ar_ma_config(self) -> None:
        """Test Arabic Morocco configuration."""
        config = LOCALE_CONFIGS[Locale.AR_MA]
        assert config.language == "ar"
        assert config.region == "MA"
        assert config.currency == Currency.MAD
        assert config.default_timezone == "Africa/Casablanca"
        assert config.text_direction == "rtl"
        assert config.first_day_of_week == 1  # Monday

    def test_fr_ma_config(self) -> None:
        """Test French Morocco configuration."""
        config = LOCALE_CONFIGS[Locale.FR_MA]
        assert config.language == "fr"
        assert config.region == "MA"
        assert config.currency == Currency.MAD
        assert config.decimal_separator == ","
        assert config.thousands_separator == " "
        assert config.text_direction == "ltr"

    def test_ar_tn_config(self) -> None:
        """Test Arabic Tunisia configuration."""
        config = LOCALE_CONFIGS[Locale.AR_TN]
        assert config.language == "ar"
        assert config.region == "TN"
        assert config.currency == Currency.TND
        assert config.default_timezone == "Africa/Tunis"

    def test_fr_tn_config(self) -> None:
        """Test French Tunisia configuration."""
        config = LOCALE_CONFIGS[Locale.FR_TN]
        assert config.language == "fr"
        assert config.region == "TN"
        assert config.currency == Currency.TND

    def test_en_us_config(self) -> None:
        """Test English US configuration."""
        config = LOCALE_CONFIGS[Locale.EN_US]
        assert config.decimal_separator == "."
        assert config.thousands_separator == ","
        assert config.first_day_of_week == 0  # Sunday


# ============================================================
# Month/Day Names Tests
# ============================================================


class TestNameConstants:
    """Test month and day name constants."""

    def test_french_months(self) -> None:
        """Test French month names."""
        assert len(MONTH_NAMES_FR) == 12
        assert MONTH_NAMES_FR[0] == "janvier"
        assert MONTH_NAMES_FR[11] == "décembre"

    def test_arabic_months(self) -> None:
        """Test Arabic month names."""
        assert len(MONTH_NAMES_AR) == 12
        assert MONTH_NAMES_AR[0] == "يناير"

    def test_english_months(self) -> None:
        """Test English month names."""
        assert len(MONTH_NAMES_EN) == 12
        assert MONTH_NAMES_EN[0] == "January"

    def test_french_days(self) -> None:
        """Test French day names."""
        assert len(DAY_NAMES_FR) == 7
        assert DAY_NAMES_FR[0] == "lundi"  # Monday first

    def test_arabic_days(self) -> None:
        """Test Arabic day names."""
        assert len(DAY_NAMES_AR) == 7
        assert DAY_NAMES_AR[4] == "الجمعة"  # Friday

    def test_english_days(self) -> None:
        """Test English day names."""
        assert len(DAY_NAMES_EN) == 7
        assert DAY_NAMES_EN[0] == "Monday"


# ============================================================
# Service Initialization Tests
# ============================================================


class TestServiceInitialization:
    """Test service initialization."""

    def test_default_locale(self) -> None:
        """Test default locale is French Morocco."""
        service = LocaleFormatsService()
        assert service.get_default_locale() == Locale.FR_MA

    def test_custom_default_locale(self) -> None:
        """Test custom default locale."""
        service = LocaleFormatsService(default_locale=Locale.AR_TN)
        assert service.get_default_locale() == Locale.AR_TN

    def test_set_default_locale(self, service: LocaleFormatsService) -> None:
        """Test setting default locale."""
        service.set_default_locale(Locale.EN_US)
        assert service.get_default_locale() == Locale.EN_US


# ============================================================
# User Locale Tests
# ============================================================


class TestUserLocale:
    """Test user locale management."""

    def test_get_user_locale_default(self, service: LocaleFormatsService) -> None:
        """Test getting user locale returns default."""
        locale = service.get_user_locale("user-123")
        assert locale == Locale.FR_MA

    def test_set_user_locale(self, service: LocaleFormatsService) -> None:
        """Test setting user locale."""
        service.set_user_locale("user-123", Locale.AR_MA)
        assert service.get_user_locale("user-123") == Locale.AR_MA

    def test_multiple_users(self, service: LocaleFormatsService) -> None:
        """Test multiple users with different locales."""
        service.set_user_locale("user-1", Locale.AR_MA)
        service.set_user_locale("user-2", Locale.FR_TN)
        service.set_user_locale("user-3", Locale.EN_US)

        assert service.get_user_locale("user-1") == Locale.AR_MA
        assert service.get_user_locale("user-2") == Locale.FR_TN
        assert service.get_user_locale("user-3") == Locale.EN_US


# ============================================================
# Date Formatting Tests
# ============================================================


class TestDateFormatting:
    """Test date formatting."""

    def test_format_date_iso(self, service: LocaleFormatsService, sample_date: date) -> None:
        """Test ISO date format."""
        result = service.format_date(sample_date, style=DateFormat.ISO)
        assert result.value == "2024-01-15"

    def test_format_date_short_fr(self, service: LocaleFormatsService, sample_date: date) -> None:
        """Test short date format in French."""
        result = service.format_date(sample_date, locale=Locale.FR_MA, style=DateFormat.SHORT)
        assert result.value == "15/01/24"

    def test_format_date_medium_fr(self, service: LocaleFormatsService, sample_date: date) -> None:
        """Test medium date format in French."""
        result = service.format_date(sample_date, locale=Locale.FR_MA, style=DateFormat.MEDIUM)
        assert "janv." in result.value
        assert "15" in result.value
        assert "2024" in result.value

    def test_format_date_long_fr(self, service: LocaleFormatsService, sample_date: date) -> None:
        """Test long date format in French."""
        result = service.format_date(sample_date, locale=Locale.FR_MA, style=DateFormat.LONG)
        assert "janvier" in result.value
        assert "15" in result.value
        assert "2024" in result.value

    def test_format_date_full_fr(self, service: LocaleFormatsService, sample_date: date) -> None:
        """Test full date format in French."""
        result = service.format_date(sample_date, locale=Locale.FR_MA, style=DateFormat.FULL)
        assert "lundi" in result.value  # January 15, 2024 is Monday
        assert "janvier" in result.value

    def test_format_date_arabic(self, service: LocaleFormatsService, sample_date: date) -> None:
        """Test date format in Arabic."""
        result = service.format_date(sample_date, locale=Locale.AR_MA, style=DateFormat.LONG)
        assert "يناير" in result.value
        assert result.is_rtl is True

    def test_format_date_english(self, service: LocaleFormatsService, sample_date: date) -> None:
        """Test date format in English."""
        result = service.format_date(sample_date, locale=Locale.EN_US, style=DateFormat.LONG)
        assert "January" in result.value

    def test_format_datetime_as_date(
        self,
        service: LocaleFormatsService,
        sample_datetime: datetime,
    ) -> None:
        """Test formatting datetime as date."""
        result = service.format_date(sample_datetime, style=DateFormat.ISO)
        assert result.value == "2024-01-15"


# ============================================================
# Date Parsing Tests
# ============================================================


class TestDateParsing:
    """Test date parsing."""

    def test_parse_date_iso(self, service: LocaleFormatsService) -> None:
        """Test parsing ISO date."""
        result = service.parse_date("2024-01-15", style=DateFormat.ISO)
        assert result == date(2024, 1, 15)

    def test_parse_date_short_fr(self, service: LocaleFormatsService) -> None:
        """Test parsing short French date."""
        result = service.parse_date("15/01/24", locale=Locale.FR_MA, style=DateFormat.SHORT)
        assert result == date(2024, 1, 15)

    def test_parse_date_short_full_year(self, service: LocaleFormatsService) -> None:
        """Test parsing with full year."""
        result = service.parse_date("15/01/2024", locale=Locale.FR_MA, style=DateFormat.SHORT)
        assert result == date(2024, 1, 15)

    def test_parse_date_invalid(self, service: LocaleFormatsService) -> None:
        """Test parsing invalid date."""
        result = service.parse_date("invalid", style=DateFormat.ISO)
        assert result is None

    def test_parse_date_wrong_format(self, service: LocaleFormatsService) -> None:
        """Test parsing wrong format."""
        result = service.parse_date("2024-01-15", style=DateFormat.SHORT)
        assert result is None


# ============================================================
# Time Formatting Tests
# ============================================================


class TestTimeFormatting:
    """Test time formatting."""

    def test_format_time_short(self, service: LocaleFormatsService, sample_time: time) -> None:
        """Test short time format."""
        result = service.format_time(sample_time, style=TimeFormat.SHORT)
        assert result.value == "14:30"

    def test_format_time_medium(self, service: LocaleFormatsService, sample_time: time) -> None:
        """Test medium time format."""
        result = service.format_time(sample_time, style=TimeFormat.MEDIUM)
        assert result.value == "14:30:45"

    def test_format_time_long(self, service: LocaleFormatsService, sample_time: time) -> None:
        """Test long time format."""
        result = service.format_time(sample_time, style=TimeFormat.LONG)
        assert "14:30:45" in result.value
        assert "UTC" in result.value

    def test_format_time_12h(self, service: LocaleFormatsService, sample_time: time) -> None:
        """Test 12-hour format."""
        result = service.format_time(sample_time, style=TimeFormat.TWELVE_HOUR)
        assert "2:30" in result.value
        assert "PM" in result.value

    def test_format_time_12h_am(self, service: LocaleFormatsService) -> None:
        """Test 12-hour format AM."""
        t = time(9, 15, 0)
        result = service.format_time(t, style=TimeFormat.TWELVE_HOUR)
        assert "9:15" in result.value
        assert "AM" in result.value

    def test_format_time_12h_midnight(self, service: LocaleFormatsService) -> None:
        """Test 12-hour format midnight."""
        t = time(0, 30, 0)
        result = service.format_time(t, style=TimeFormat.TWELVE_HOUR)
        assert "12:30" in result.value
        assert "AM" in result.value

    def test_format_time_12h_noon(self, service: LocaleFormatsService) -> None:
        """Test 12-hour format noon."""
        t = time(12, 0, 0)
        result = service.format_time(t, style=TimeFormat.TWELVE_HOUR)
        assert "12:00" in result.value
        assert "PM" in result.value

    def test_format_datetime_time(
        self,
        service: LocaleFormatsService,
        sample_datetime: datetime,
    ) -> None:
        """Test formatting datetime as time."""
        result = service.format_time(sample_datetime, style=TimeFormat.SHORT)
        assert result.value == "14:30"


# ============================================================
# Datetime Formatting Tests
# ============================================================


class TestDatetimeFormatting:
    """Test datetime formatting."""

    def test_format_datetime(
        self,
        service: LocaleFormatsService,
        sample_datetime: datetime,
    ) -> None:
        """Test datetime formatting."""
        result = service.format_datetime(sample_datetime)
        assert "15" in result.value
        assert "14:30" in result.value

    def test_format_datetime_custom_styles(
        self,
        service: LocaleFormatsService,
        sample_datetime: datetime,
    ) -> None:
        """Test datetime with custom styles."""
        result = service.format_datetime(
            sample_datetime,
            date_style=DateFormat.LONG,
            time_style=TimeFormat.MEDIUM,
        )
        assert "janvier" in result.value
        assert "14:30:45" in result.value


# ============================================================
# Number Formatting Tests
# ============================================================


class TestNumberFormatting:
    """Test number formatting."""

    def test_format_number_french(self, service: LocaleFormatsService) -> None:
        """Test French number format."""
        result = service.format_number(1234567.89, locale=Locale.FR_MA)
        assert "," in result.value  # French decimal separator
        assert " " in result.value  # French thousands separator
        assert "1 234 567,89" == result.value

    def test_format_number_english(self, service: LocaleFormatsService) -> None:
        """Test English number format."""
        result = service.format_number(1234567.89, locale=Locale.EN_US)
        assert "." in result.value  # English decimal separator
        assert "," in result.value  # English thousands separator
        assert "1,234,567.89" == result.value

    def test_format_number_custom_decimals(self, service: LocaleFormatsService) -> None:
        """Test custom decimal places."""
        result = service.format_number(1234.5678, locale=Locale.EN_US, decimal_places=4)
        assert result.value == "1,234.5678"

    def test_format_number_zero_decimals(self, service: LocaleFormatsService) -> None:
        """Test zero decimal places."""
        result = service.format_number(1234.567, locale=Locale.EN_US, decimal_places=0)
        assert result.value == "1,234"

    def test_format_number_negative(self, service: LocaleFormatsService) -> None:
        """Test negative number."""
        result = service.format_number(-1234.56, locale=Locale.FR_MA)
        assert result.value.startswith("-")
        assert "1 234,56" in result.value

    def test_format_number_percent(self, service: LocaleFormatsService) -> None:
        """Test percent format."""
        result = service.format_number(0.85, locale=Locale.EN_US, style=NumberFormat.PERCENT)
        assert "85" in result.value
        assert "%" in result.value

    def test_format_number_scientific(self, service: LocaleFormatsService) -> None:
        """Test scientific format."""
        result = service.format_number(1234567, locale=Locale.EN_US, style=NumberFormat.SCIENTIFIC)
        assert "e" in result.value.lower()

    def test_format_number_decimal_type(self, service: LocaleFormatsService) -> None:
        """Test formatting Decimal type."""
        result = service.format_number(Decimal("1234.56"), locale=Locale.EN_US)
        assert result.value == "1,234.56"

    def test_format_number_small(self, service: LocaleFormatsService) -> None:
        """Test small number without thousands separator."""
        result = service.format_number(123.45, locale=Locale.FR_MA)
        assert result.value == "123,45"


# ============================================================
# Number Parsing Tests
# ============================================================


class TestNumberParsing:
    """Test number parsing."""

    def test_parse_number_french(self, service: LocaleFormatsService) -> None:
        """Test parsing French number."""
        result = service.parse_number("1 234,56", locale=Locale.FR_MA)
        assert result == 1234.56

    def test_parse_number_english(self, service: LocaleFormatsService) -> None:
        """Test parsing English number."""
        result = service.parse_number("1,234.56", locale=Locale.EN_US)
        assert result == 1234.56

    def test_parse_number_percent(self, service: LocaleFormatsService) -> None:
        """Test parsing percentage."""
        result = service.parse_number("85 %", locale=Locale.FR_MA)
        assert result == 85.0

    def test_parse_number_invalid(self, service: LocaleFormatsService) -> None:
        """Test parsing invalid number."""
        result = service.parse_number("not a number")
        assert result is None


# ============================================================
# Currency Formatting Tests
# ============================================================


class TestCurrencyFormatting:
    """Test currency formatting."""

    def test_format_currency_mad(self, service: LocaleFormatsService) -> None:
        """Test MAD currency format."""
        result = service.format_currency(1234.56, currency=Currency.MAD, locale=Locale.FR_MA)
        assert "1 234,56" in result.value
        assert "د.م." in result.value

    def test_format_currency_tnd(self, service: LocaleFormatsService) -> None:
        """Test TND currency format (3 decimals)."""
        result = service.format_currency(1234.567, currency=Currency.TND, locale=Locale.FR_TN)
        assert "567" in result.value  # 3 decimal places
        assert "د.ت" in result.value

    def test_format_currency_usd(self, service: LocaleFormatsService) -> None:
        """Test USD currency format."""
        result = service.format_currency(1234.56, currency=Currency.USD, locale=Locale.EN_US)
        assert "$" in result.value
        assert result.value.startswith("$")  # Symbol before

    def test_format_currency_eur(self, service: LocaleFormatsService) -> None:
        """Test EUR currency format."""
        result = service.format_currency(1234.56, currency=Currency.EUR, locale=Locale.FR_FR)
        assert "€" in result.value

    def test_format_currency_default(self, service: LocaleFormatsService) -> None:
        """Test currency format uses locale default."""
        result = service.format_currency(100.00, locale=Locale.AR_TN)
        assert "د.ت" in result.value  # TND is default for Tunisia

    def test_format_currency_custom_decimals(self, service: LocaleFormatsService) -> None:
        """Test currency with custom decimal places."""
        result = service.format_currency(
            1234.5,
            currency=Currency.MAD,
            locale=Locale.FR_MA,
            decimal_places=0,
        )
        assert "1 234" in result.value  # Truncated to 0 decimal places

    def test_format_currency_code(self, service: LocaleFormatsService) -> None:
        """Test currency format with ISO code."""
        result = service.format_currency_code(1234.56, currency=Currency.MAD, locale=Locale.FR_MA)
        assert "MAD" in result.value
        assert "1 234,56" in result.value


# ============================================================
# Currency Info Tests
# ============================================================


class TestCurrencyInfoService:
    """Test currency info service methods."""

    def test_get_currency_info(self, service: LocaleFormatsService) -> None:
        """Test getting currency info."""
        info = service.get_currency_info(Currency.MAD)
        assert info.code == "MAD"
        assert info.symbol == "د.م."

    def test_get_all_currencies(self, service: LocaleFormatsService) -> None:
        """Test getting all currencies."""
        currencies = service.get_all_currencies()
        assert len(currencies) == 5
        codes = [c.code for c in currencies]
        assert "MAD" in codes
        assert "TND" in codes


# ============================================================
# Relative Time Tests
# ============================================================


class TestRelativeTime:
    """Test relative time formatting."""

    def test_relative_time_just_now(self, service: LocaleFormatsService) -> None:
        """Test just now."""
        now = datetime.now(timezone.utc)
        result = service.format_relative_time(now - timedelta(seconds=30))
        # Default is French
        assert "instant" in result.value or "now" in result.value

    def test_relative_time_minutes_fr(self, service: LocaleFormatsService) -> None:
        """Test minutes ago in French."""
        now = datetime.now(timezone.utc)
        result = service.format_relative_time(
            now - timedelta(minutes=5),
            reference=now,
            locale=Locale.FR_MA,
        )
        assert "5 minute" in result.value
        assert "il y a" in result.value

    def test_relative_time_hours_fr(self, service: LocaleFormatsService) -> None:
        """Test hours ago in French."""
        now = datetime.now(timezone.utc)
        result = service.format_relative_time(
            now - timedelta(hours=3),
            reference=now,
            locale=Locale.FR_MA,
        )
        assert "3 heure" in result.value

    def test_relative_time_days_fr(self, service: LocaleFormatsService) -> None:
        """Test days ago in French."""
        now = datetime.now(timezone.utc)
        result = service.format_relative_time(
            now - timedelta(days=2),
            reference=now,
            locale=Locale.FR_MA,
        )
        assert "2 jour" in result.value

    def test_relative_time_weeks_fr(self, service: LocaleFormatsService) -> None:
        """Test weeks ago in French."""
        now = datetime.now(timezone.utc)
        result = service.format_relative_time(
            now - timedelta(weeks=2),
            reference=now,
            locale=Locale.FR_MA,
        )
        assert "2 semaine" in result.value

    def test_relative_time_months_fr(self, service: LocaleFormatsService) -> None:
        """Test months ago in French."""
        now = datetime.now(timezone.utc)
        result = service.format_relative_time(
            now - timedelta(days=60),
            reference=now,
            locale=Locale.FR_MA,
        )
        assert "mois" in result.value

    def test_relative_time_future_fr(self, service: LocaleFormatsService) -> None:
        """Test future time in French."""
        now = datetime.now(timezone.utc)
        result = service.format_relative_time(
            now + timedelta(hours=2),
            reference=now,
            locale=Locale.FR_MA,
        )
        assert "dans" in result.value

    def test_relative_time_ar(self, service: LocaleFormatsService) -> None:
        """Test relative time in Arabic."""
        now = datetime.now(timezone.utc)
        result = service.format_relative_time(
            now - timedelta(hours=5),
            reference=now,
            locale=Locale.AR_MA,
        )
        assert "منذ" in result.value
        assert result.is_rtl is True

    def test_relative_time_en(self, service: LocaleFormatsService) -> None:
        """Test relative time in English."""
        now = datetime.now(timezone.utc)
        result = service.format_relative_time(
            now - timedelta(days=3),
            reference=now,
            locale=Locale.EN_US,
        )
        assert "3 days ago" in result.value


# ============================================================
# Duration Formatting Tests
# ============================================================


class TestDurationFormatting:
    """Test duration formatting."""

    def test_format_duration_seconds(self, service: LocaleFormatsService) -> None:
        """Test duration in seconds."""
        result = service.format_duration(45, locale=Locale.EN_US)
        assert "45s" in result.value

    def test_format_duration_minutes(self, service: LocaleFormatsService) -> None:
        """Test duration in minutes."""
        result = service.format_duration(125, locale=Locale.EN_US)
        assert "2m" in result.value
        assert "5s" in result.value

    def test_format_duration_hours(self, service: LocaleFormatsService) -> None:
        """Test duration in hours."""
        result = service.format_duration(3725, locale=Locale.EN_US)
        assert "1h" in result.value
        assert "2m" in result.value
        assert "5s" in result.value

    def test_format_duration_no_seconds(self, service: LocaleFormatsService) -> None:
        """Test duration without seconds."""
        result = service.format_duration(3725, locale=Locale.EN_US, include_seconds=False)
        assert "1h" in result.value
        assert "2m" in result.value
        assert "s" not in result.value

    def test_format_duration_french(self, service: LocaleFormatsService) -> None:
        """Test duration in French."""
        result = service.format_duration(3725, locale=Locale.FR_MA)
        assert "1h" in result.value
        assert "2min" in result.value

    def test_format_duration_arabic(self, service: LocaleFormatsService) -> None:
        """Test duration in Arabic."""
        result = service.format_duration(3725, locale=Locale.AR_MA)
        assert "س" in result.value  # Hour abbreviation
        assert "د" in result.value  # Minute abbreviation

    def test_format_duration_zero(self, service: LocaleFormatsService) -> None:
        """Test zero duration."""
        result = service.format_duration(0, locale=Locale.EN_US)
        assert "0s" in result.value


# ============================================================
# Utility Method Tests
# ============================================================


class TestUtilityMethods:
    """Test utility methods."""

    def test_get_timezone_ma(self, service: LocaleFormatsService) -> None:
        """Test getting Morocco timezone."""
        tz = service.get_timezone_for_locale(Locale.FR_MA)
        assert tz == "Africa/Casablanca"

    def test_get_timezone_tn(self, service: LocaleFormatsService) -> None:
        """Test getting Tunisia timezone."""
        tz = service.get_timezone_for_locale(Locale.AR_TN)
        assert tz == "Africa/Tunis"

    def test_get_first_day_of_week_ma(self, service: LocaleFormatsService) -> None:
        """Test first day of week in Morocco."""
        day = service.get_first_day_of_week(Locale.FR_MA)
        assert day == 1  # Monday

    def test_get_first_day_of_week_us(self, service: LocaleFormatsService) -> None:
        """Test first day of week in US."""
        day = service.get_first_day_of_week(Locale.EN_US)
        assert day == 0  # Sunday

    def test_is_rtl_arabic(self, service: LocaleFormatsService) -> None:
        """Test RTL for Arabic."""
        assert service.is_rtl(Locale.AR_MA) is True
        assert service.is_rtl(Locale.AR_TN) is True

    def test_is_rtl_french(self, service: LocaleFormatsService) -> None:
        """Test RTL for French."""
        assert service.is_rtl(Locale.FR_MA) is False
        assert service.is_rtl(Locale.FR_TN) is False

    def test_get_language(self, service: LocaleFormatsService) -> None:
        """Test getting language code."""
        assert service.get_language(Locale.AR_MA) == "ar"
        assert service.get_language(Locale.FR_MA) == "fr"
        assert service.get_language(Locale.EN_US) == "en"

    def test_get_region(self, service: LocaleFormatsService) -> None:
        """Test getting region code."""
        assert service.get_region(Locale.AR_MA) == "MA"
        assert service.get_region(Locale.FR_TN) == "TN"
        assert service.get_region(Locale.EN_US) == "US"

    def test_get_locale_config(self, service: LocaleFormatsService) -> None:
        """Test getting locale config."""
        config = service.get_locale_config(Locale.FR_MA)
        assert config.locale == Locale.FR_MA
        assert config.language == "fr"

    def test_get_all_locales(self, service: LocaleFormatsService) -> None:
        """Test getting all locales."""
        locales = service.get_all_locales()
        assert len(locales) == 7
        assert Locale.AR_MA in locales
        assert Locale.FR_TN in locales

    def test_get_morocco_locales(self, service: LocaleFormatsService) -> None:
        """Test getting Morocco locales."""
        locales = service.get_morocco_locales()
        assert len(locales) == 2
        assert Locale.AR_MA in locales
        assert Locale.FR_MA in locales

    def test_get_tunisia_locales(self, service: LocaleFormatsService) -> None:
        """Test getting Tunisia locales."""
        locales = service.get_tunisia_locales()
        assert len(locales) == 2
        assert Locale.AR_TN in locales
        assert Locale.FR_TN in locales


# ============================================================
# Edge Cases
# ============================================================


class TestEdgeCases:
    """Test edge cases."""

    def test_format_date_leap_year(self, service: LocaleFormatsService) -> None:
        """Test formatting leap year date."""
        d = date(2024, 2, 29)
        result = service.format_date(d, locale=Locale.FR_MA, style=DateFormat.LONG)
        assert "29" in result.value
        assert "février" in result.value

    def test_format_time_midnight(self, service: LocaleFormatsService) -> None:
        """Test formatting midnight."""
        t = time(0, 0, 0)
        result = service.format_time(t, style=TimeFormat.SHORT)
        assert result.value == "00:00"

    def test_format_time_end_of_day(self, service: LocaleFormatsService) -> None:
        """Test formatting end of day."""
        t = time(23, 59, 59)
        result = service.format_time(t, style=TimeFormat.MEDIUM)
        assert "23:59:59" in result.value

    def test_format_number_zero(self, service: LocaleFormatsService) -> None:
        """Test formatting zero."""
        result = service.format_number(0, locale=Locale.FR_MA)
        assert result.value == "0,00"

    def test_format_number_very_large(self, service: LocaleFormatsService) -> None:
        """Test formatting very large number."""
        result = service.format_number(1234567890123.45, locale=Locale.FR_MA)
        assert " " in result.value  # Has thousands separators

    def test_format_number_very_small(self, service: LocaleFormatsService) -> None:
        """Test formatting very small decimal."""
        result = service.format_number(0.01, locale=Locale.FR_MA)
        assert "0,01" == result.value

    def test_format_currency_zero(self, service: LocaleFormatsService) -> None:
        """Test formatting zero currency."""
        result = service.format_currency(0, currency=Currency.MAD, locale=Locale.FR_MA)
        assert "0,00" in result.value

    def test_format_currency_negative(self, service: LocaleFormatsService) -> None:
        """Test formatting negative currency."""
        result = service.format_currency(-1234.56, currency=Currency.MAD, locale=Locale.FR_MA)
        assert "-" in result.value

    def test_relative_time_naive_datetime(self, service: LocaleFormatsService) -> None:
        """Test relative time with naive datetime."""
        now = datetime.now()  # Naive
        past = now - timedelta(hours=1)
        result = service.format_relative_time(past, reference=now, locale=Locale.EN_US)
        assert "1 hour ago" in result.value


# ============================================================
# Integration Tests
# ============================================================


class TestIntegration:
    """Integration tests."""

    def test_full_formatting_workflow(self, service: LocaleFormatsService) -> None:
        """Test complete formatting workflow."""
        # Set user locale
        service.set_user_locale("user-123", Locale.AR_MA)
        locale = service.get_user_locale("user-123")

        # Format date
        d = date(2024, 1, 15)
        date_result = service.format_date(d, locale=locale, style=DateFormat.FULL)
        assert date_result.is_rtl is True
        assert "يناير" in date_result.value

        # Format currency
        amount = 1500.50
        curr_result = service.format_currency(amount, locale=locale)
        assert "د.م." in curr_result.value

    def test_morocco_business_scenario(self, service: LocaleFormatsService) -> None:
        """Test Morocco business scenario."""
        # Quote amount in MAD
        quote_amount = 15750.00
        result = service.format_currency(quote_amount, currency=Currency.MAD, locale=Locale.FR_MA)
        assert "15 750,00" in result.value
        assert "د.م." in result.value

        # Quote date
        quote_date = date(2024, 3, 15)
        date_result = service.format_date(quote_date, locale=Locale.FR_MA, style=DateFormat.LONG)
        assert "mars" in date_result.value

    def test_tunisia_business_scenario(self, service: LocaleFormatsService) -> None:
        """Test Tunisia business scenario."""
        # Invoice amount in TND (3 decimals)
        invoice_amount = 2500.750
        result = service.format_currency(invoice_amount, currency=Currency.TND, locale=Locale.FR_TN)
        assert "750" in result.value  # 3 decimal places
        assert "د.ت" in result.value

    def test_multilingual_report(self, service: LocaleFormatsService) -> None:
        """Test generating multilingual report."""
        d = date(2024, 6, 15)
        amount = 5000.00

        # French version
        fr_date = service.format_date(d, locale=Locale.FR_MA, style=DateFormat.LONG)
        fr_amount = service.format_currency(amount, currency=Currency.MAD, locale=Locale.FR_MA)
        assert "juin" in fr_date.value

        # Arabic version
        ar_date = service.format_date(d, locale=Locale.AR_MA, style=DateFormat.LONG)
        ar_amount = service.format_currency(amount, currency=Currency.MAD, locale=Locale.AR_MA)
        assert "يونيو" in ar_date.value
        assert ar_date.is_rtl is True
