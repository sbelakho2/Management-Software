//! Value objects for the Sensei ERP system.
//!
//! Value objects are immutable, equality-comparable types that represent
//! concepts without a distinct identity (unlike entities).

use crate::error::SenseiError;
use regex::Regex;
use serde::{Deserialize, Serialize};
use std::sync::OnceLock;

/// An email address value object.
///
/// Provides validation and normalization. Validation follows a pragmatic
/// RFC-5322-ish pattern: a local part of letters, digits, and `._%+-`,
/// followed by `@`, then a domain with at least one dot whose labels start
/// and end with an alphanumeric character and whose TLD is alphabetic.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct EmailAddress(String);

impl EmailAddress {
    /// Create a new [`EmailAddress`] after validation.
    ///
    /// Returns `None` if the email is invalid.
    pub fn new(email: impl Into<String>) -> Option<Self> {
        let email = email.into().trim().to_lowercase();
        if email.len() > 320 || !email_regex().is_match(&email) {
            return None;
        }
        Some(Self(email))
    }

    /// Returns the inner email string.
    pub fn as_str(&self) -> &str {
        &self.0
    }
}

/// Pragmatic RFC-5322-ish email pattern.
///
/// - local part: one or more of `A-Za-z0-9._%+-`
/// - `@`
/// - domain: at least two labels, first label `[A-Za-z0-9]([A-Za-z0-9-]*[A-Za-z0-9])?`
///   (no leading/trailing hyphen), further labels separated by `.`, and a
///   final alphabetic TLD of at least 2 characters.
static EMAIL_REGEX: OnceLock<Regex> = OnceLock::new();

fn email_regex() -> &'static Regex {
    EMAIL_REGEX.get_or_init(|| {
        Regex::new(
            r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9]([A-Za-z0-9-]*[A-Za-z0-9])?(\.[A-Za-z0-9]([A-Za-z0-9-]*[A-Za-z0-9])?)*\.[A-Za-z]{2,}$",
        )
        .expect("email validation regex is valid")
    })
}

impl std::fmt::Display for EmailAddress {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}", self.0)
    }
}

/// A phone number value object.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct PhoneNumber(String);

impl PhoneNumber {
    /// Create a new [`PhoneNumber`].
    pub fn new(phone: impl Into<String>) -> Self {
        Self(phone.into())
    }

    /// Returns the inner phone number string.
    pub fn as_str(&self) -> &str {
        &self.0
    }
}

impl std::fmt::Display for PhoneNumber {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}", self.0)
    }
}

/// A monetary amount value object.
///
/// Stores the amount as integer cents to avoid floating-point precision issues.
#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq, PartialOrd, Ord)]
pub struct Money {
    /// Amount in the smallest currency unit (cents).
    pub cents: i64,
    /// ISO 4217 currency code (e.g., "USD", "EUR", "MAD").
    pub currency: CurrencyCode,
}

impl Money {
    /// Create a new [`Money`] from cents.
    pub fn from_cents(cents: i64, currency: CurrencyCode) -> Self {
        Self { cents, currency }
    }

    /// Create a new [`Money`] from a decimal amount (e.g., 10.50 for $10.50).
    ///
    /// Multiplies by 100 and rounds to the nearest cent. Rejects NaN and
    /// infinite values.
    pub fn from_decimal(amount: f64, currency: CurrencyCode) -> Result<Self, SenseiError> {
        if !amount.is_finite() {
            return Err(SenseiError::Validation(
                "Money amount must be a finite number".to_string(),
            ));
        }
        let cents = (amount * 100.0).round() as i64;
        Ok(Self { cents, currency })
    }

    /// Decimal-NATIVE construction (twenty-first audit item 14): money is
    /// built from the Decimal aggregate directly — no f64 round trip at
    /// the constructor boundary. Minor units are computed with Decimal
    /// arithmetic (multiply by 100, truncate toward zero).
    pub fn from_decimal_decimal(
        amount: rust_decimal::Decimal,
        currency: CurrencyCode,
    ) -> Result<Self, SenseiError> {
        let scaled = amount
            .checked_mul(rust_decimal::Decimal::from(100))
            .ok_or_else(|| {
                SenseiError::Validation("Money amount overflowed minor-unit scaling".to_string())
            })?;
        let cents =
            rust_decimal::prelude::ToPrimitive::to_i64(&scaled.round_dp(0)).unwrap_or(i64::MAX);
        Ok(Self { cents, currency })
    }

    /// Returns the amount as a decimal value (e.g., 10.50).
    pub fn to_decimal(&self) -> f64 {
        self.cents as f64 / 100.0
    }
}

impl std::fmt::Display for Money {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{:.2} {}", self.to_decimal(), self.currency)
    }
}

/// ISO 4217 currency code.
#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub enum CurrencyCode {
    /// US Dollar.
    USD,
    /// Euro.
    EUR,
    /// British Pound.
    GBP,
    /// Moroccan Dirham.
    MAD,
    /// Japanese Yen.
    JPY,
    /// Chinese Yuan.
    CNY,
}

impl CurrencyCode {
    /// Returns the string representation of this currency code.
    pub fn as_str(&self) -> &'static str {
        match self {
            CurrencyCode::USD => "USD",
            CurrencyCode::EUR => "EUR",
            CurrencyCode::GBP => "GBP",
            CurrencyCode::MAD => "MAD",
            CurrencyCode::JPY => "JPY",
            CurrencyCode::CNY => "CNY",
        }
    }
}

impl std::fmt::Display for CurrencyCode {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}", self.as_str())
    }
}

/// A physical address value object.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct Address {
    /// Street address (including number).
    pub street: String,
    /// City.
    pub city: String,
    /// State/Province/Region.
    pub state: Option<String>,
    /// Postal/ZIP code.
    pub postal_code: String,
    /// Country.
    pub country: String,
}

impl std::fmt::Display for Address {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}, {}", self.street, self.city)?;
        if let Some(state) = &self.state {
            write!(f, ", {}", state)?;
        }
        write!(f, " {} {}", self.postal_code, self.country)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn email_address_accepts_valid_addresses() {
        assert!(EmailAddress::new("a@b.co").is_some());
        assert!(EmailAddress::new("user.name+tag@sub.example.com").is_some());
        assert!(EmailAddress::new("first.last@Example.ORG").is_some());
    }

    #[test]
    fn email_address_rejects_invalid_addresses() {
        assert!(EmailAddress::new("a@b").is_none());
        assert!(EmailAddress::new("@b.co").is_none());
        assert!(EmailAddress::new("a b@c.com").is_none());
        assert!(EmailAddress::new("a@-b.com").is_none());
        assert!(EmailAddress::new("a@b-.com").is_none());
        assert!(EmailAddress::new("a@b.c").is_none());
        assert!(EmailAddress::new("a@b.c0m").is_none());
    }

    #[test]
    fn email_address_normalizes_case_and_whitespace() {
        let email = EmailAddress::new("  USER@Example.COM ").expect("valid email");
        assert_eq!(email.as_str(), "user@example.com");
    }

    #[test]
    fn money_from_decimal_rounds_to_nearest_cent() {
        assert_eq!(
            Money::from_decimal(10.505, CurrencyCode::USD)
                .unwrap()
                .cents,
            1051
        );
        assert_eq!(
            Money::from_decimal(10.5, CurrencyCode::USD).unwrap().cents,
            1050
        );
        assert_eq!(
            Money::from_decimal(-std::f64::consts::PI, CurrencyCode::EUR)
                .unwrap()
                .cents,
            -314
        );
    }

    #[test]
    fn money_from_decimal_rejects_non_finite() {
        assert!(Money::from_decimal(f64::NAN, CurrencyCode::USD).is_err());
        assert!(Money::from_decimal(f64::INFINITY, CurrencyCode::USD).is_err());
        assert!(Money::from_decimal(f64::NEG_INFINITY, CurrencyCode::USD).is_err());
    }

    #[test]
    fn money_round_trip() {
        let money = Money::from_decimal(123.45, CurrencyCode::MAD).unwrap();
        assert_eq!(money.to_decimal(), 123.45);
        assert_eq!(money.cents, 12345);
    }
}
