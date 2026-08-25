//! Password hashing using the Argon2 algorithm.
//!
//! Argon2 is the recommended password hashing algorithm by OWASP and
//! provides resistance against GPU-based brute-force attacks.

use argon2::{
    password_hash::{rand_core::OsRng, PasswordHash, PasswordHasher, PasswordVerifier, SaltString},
    Argon2,
};
use sensei_core::error::{Result, SenseiError};

/// Hash a plaintext password using Argon2id.
///
/// # Arguments
/// * `password` - The plaintext password to hash.
///
/// # Returns
/// The PHC-formatted hash string (e.g., `$argon2id$v=19$...`).
pub fn hash_password(password: &str) -> Result<String> {
    let salt = SaltString::generate(&mut OsRng);
    let argon2 = Argon2::default();

    let hash = argon2
        .hash_password(password.as_bytes(), &salt)
        .map_err(|e| SenseiError::Internal(format!("Password hashing failed: {e}")))?;

    Ok(hash.to_string())
}

/// Result of a password verification attempt.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum PasswordCheck {
    /// The password matches the stored hash.
    Valid,
    /// The password does not match the stored hash.
    Invalid,
    /// The stored hash is unparseable (corrupt or not an Argon2 PHC string).
    Malformed,
}

/// Verify a plaintext password against a stored hash.
///
/// # Arguments
/// * `password` - The plaintext password to verify.
/// * `hash` - The stored PHC-formatted hash string.
///
/// # Returns
/// * [`PasswordCheck::Valid`] if the password matches the hash.
/// * [`PasswordCheck::Invalid`] if the password does not match.
/// * [`PasswordCheck::Malformed`] if the stored hash cannot be parsed —
///   this is distinct from a wrong password so callers can treat corrupt
///   hashes differently (e.g. force a password reset).
pub fn verify_password(password: &str, hash: &str) -> Result<PasswordCheck> {
    let parsed_hash = match PasswordHash::new(hash) {
        Ok(h) => h,
        Err(_) => return Ok(PasswordCheck::Malformed),
    };

    let argon2 = Argon2::default();
    match argon2.verify_password(password.as_bytes(), &parsed_hash) {
        Ok(()) => Ok(PasswordCheck::Valid),
        Err(_) => Ok(PasswordCheck::Invalid),
    }
}

/// Check if a password meets the minimum complexity requirements.
///
/// Requirements:
/// - At least 8 characters
/// - At least one uppercase letter
/// - At least one lowercase letter
/// - At least one digit
/// - At least one special character
pub fn validate_password_strength(password: &str) -> Result<()> {
    if password.len() < 8 {
        return Err(SenseiError::Validation(
            "Password must be at least 8 characters".to_string(),
        ));
    }

    let has_upper = password.chars().any(|c| c.is_uppercase());
    let has_lower = password.chars().any(|c| c.is_lowercase());
    let has_digit = password.chars().any(|c| c.is_ascii_digit());
    let has_special = password.chars().any(|c| !c.is_alphanumeric());

    if !has_upper {
        return Err(SenseiError::Validation(
            "Password must contain at least one uppercase letter".to_string(),
        ));
    }
    if !has_lower {
        return Err(SenseiError::Validation(
            "Password must contain at least one lowercase letter".to_string(),
        ));
    }
    if !has_digit {
        return Err(SenseiError::Validation(
            "Password must contain at least one digit".to_string(),
        ));
    }
    if !has_special {
        return Err(SenseiError::Validation(
            "Password must contain at least one special character".to_string(),
        ));
    }

    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_hash_and_verify() {
        let password = "TestPassword123!";
        let hash = hash_password(password).unwrap();

        assert_eq!(verify_password(password, &hash).unwrap(), PasswordCheck::Valid);
        assert_eq!(
            verify_password("WrongPassword123!", &hash).unwrap(),
            PasswordCheck::Invalid
        );
    }

    #[test]
    fn test_verify_malformed_hash() {
        assert_eq!(
            verify_password("Whatever1!", "not-an-argon2-hash").unwrap(),
            PasswordCheck::Malformed
        );
        assert_eq!(verify_password("Whatever1!", "").unwrap(), PasswordCheck::Malformed);
    }

    #[test]
    fn test_password_validation() {
        assert!(validate_password_strength("ValidP@ss1").is_ok());
        assert!(validate_password_strength("short").is_err());
        assert!(validate_password_strength("nouppercase1!").is_err());
        assert!(validate_password_strength("NOLOWERCASE1!").is_err());
        assert!(validate_password_strength("NoDigits!@").is_err());
        assert!(validate_password_strength("NoSpecialChar1").is_err());
    }
}
