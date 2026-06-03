//! Value objects for the Sensei ERP system.
//!
//! Value objects are immutable, equality-comparable types that represent
//! concepts without a distinct identity (unlike entities).

use serde::{Deserialize, Serialize};

/// An email address value object.
///
/// Provides basic validation and normalization.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct EmailAddress(String);

impl EmailAddress {
    /// Create a new [`EmailAddress`] after validation.
    ///
    /// Returns `None` if the email is invalid.
    pub fn new(email: impl Into<String>) -> Option<Self> {
        let email = email.into().trim().to_lowercase();
        if email.contains('@') && email.contains('.') {
            Some(Self(email))
        } else {
            None
        }
    }

    /// Returns the inner email string.
    pub fn as_str(&self) -> &str {
        &self.0
    }
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
    /// Multiplies by 100 and rounds to nearest cent.
    pub fn from_decimal(amount: f64, currency: CurrencyCode) -> Self {
        let cents = (amount * 100.0).round() as i64;
        Self { cents, currency }
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
