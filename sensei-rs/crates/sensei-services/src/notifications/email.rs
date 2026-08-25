//! Email service implementation.
//!
//! Provides:
//! - [`EmailService`] trait for abstracted email sending
//! - [`LettreEmailService`] for production SMTP delivery via the `lettre` crate
//! - [`InMemoryEmailService`] for development/testing (stores emails in memory)

use async_trait::async_trait;
use sensei_core::error::SenseiError;
use sensei_core::types::EntityId;
use std::sync::Arc;
use tokio::sync::RwLock;

/// A record of a sent email, used by [`InMemoryEmailService`] for test assertions.
#[derive(Debug, Clone)]
pub struct SentEmail {
    /// Recipient email address.
    pub to: String,
    /// Email subject line.
    pub subject: String,
    /// HTML body content.
    pub body: String,
    /// Tenant ID that triggered this email.
    pub tenant_id: EntityId,
    /// Email type category for filtering in tests.
    pub email_type: EmailType,
}

/// Categorizes the type of email being sent.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum EmailType {
    /// Password reset email.
    PasswordReset,
    /// Email verification.
    EmailVerification,
    /// Welcome email for new users.
    Welcome,
    /// General notification.
    Notification,
    /// Daily digest email.
    DailyDigest,
}

/// Abstract email service trait.
///
/// All email sending methods accept a `tenant_id` for multi-tenant
/// isolation and return [`SenseiError`] on failure.
#[async_trait]
pub trait EmailService: Send + Sync {
    /// Send a password reset email containing a reset link with the given token.
    async fn send_password_reset(
        &self,
        email: &str,
        token: &str,
        tenant_id: EntityId,
    ) -> Result<(), SenseiError>;

    /// Send an email verification message containing a verification link with the given token.
    async fn send_email_verification(
        &self,
        email: &str,
        token: &str,
        tenant_id: EntityId,
    ) -> Result<(), SenseiError>;

    /// Send a welcome email to a newly registered user.
    async fn send_welcome_email(
        &self,
        email: &str,
        name: &str,
        tenant_id: EntityId,
    ) -> Result<(), SenseiError>;

    /// Send a general-purpose notification email.
    async fn send_notification(
        &self,
        to: &str,
        subject: &str,
        body: &str,
    ) -> Result<(), SenseiError>;

    /// Send a daily digest email with aggregated HTML content.
    async fn send_daily_digest(&self, email: &str, digest_html: &str) -> Result<(), SenseiError>;
}

// ---------------------------------------------------------------------------
// HTML Template Helpers
// ---------------------------------------------------------------------------

/// Build a complete HTML email document with a consistent branded template.
fn build_html_email(subject: &str, content: &str) -> String {
    format!(
        r#"<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>{subject}</title>
</head>
<body style="margin:0;padding:0;background-color:#f4f5f7;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color:#f4f5f7;">
        <tr>
            <td align="center" style="padding:32px 16px;">
                <table role="presentation" width="600" cellpadding="0" cellspacing="0" style="background-color:#ffffff;border-radius:8px;box-shadow:0 2px 8px rgba(0,0,0,0.08);">
                    <!-- Header -->
                    <tr>
                        <td style="padding:32px 32px 16px;text-align:center;background:linear-gradient(135deg,#1a73e8,#0d47a1);border-radius:8px 8px 0 0;">
                            <h1 style="margin:0;font-size:24px;color:#ffffff;font-weight:600;">Sensei OS</h1>
                        </td>
                    </tr>
                    <!-- Body -->
                    <tr>
                        <td style="padding:32px;color:#333333;font-size:15px;line-height:1.6;">
                            {content}
                        </td>
                    </tr>
                    <!-- Footer -->
                    <tr>
                        <td style="padding:16px 32px;border-top:1px solid #e0e0e0;text-align:center;font-size:12px;color:#999999;">
                            <p style="margin:0;">&copy; 2026 Sensei OS. All rights reserved.</p>
                            <p style="margin:4px 0 0;">This is an automated message. Please do not reply directly.</p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>"#,
        subject = subject,
        content = content
    )
}

/// Environment variable that controls the absolute base URL used in email
/// links. Defaults to `http://localhost:3000` for local development.
pub const PUBLIC_BASE_URL_ENV: &str = "PUBLIC_BASE_URL";

/// Default public base URL used when `PUBLIC_BASE_URL` is not set.
pub const DEFAULT_PUBLIC_BASE_URL: &str = "http://localhost:3000";

/// Resolve the absolute public base URL for email links.
///
/// Reads the `PUBLIC_BASE_URL` environment variable; a missing or empty
/// value falls back to [`DEFAULT_PUBLIC_BASE_URL`]. The result is trimmed of
/// trailing slashes so callers can join paths safely.
pub fn public_base_url() -> String {
    std::env::var(PUBLIC_BASE_URL_ENV)
        .ok()
        .filter(|v| !v.trim().is_empty())
        .unwrap_or_else(|| DEFAULT_PUBLIC_BASE_URL.to_string())
        .trim_end_matches('/')
        .to_string()
}

/// Build the HTML content for a password reset email.
fn build_password_reset_content(token: &str) -> String {
    let reset_link = format!("{}/reset-password?token={}", public_base_url(), token);
    format!(
        r#"<h2 style="margin:0 0 16px;font-size:20px;color:#1a73e8;">Password Reset Request</h2>
<p style="margin:0 0 16px;">We received a request to reset your password for your Sensei OS account.</p>
<p style="margin:0 0 16px;">Click the button below to reset your password. This link expires in <strong>1 hour</strong>.</p>
<table role="presentation" cellpadding="0" cellspacing="0" style="margin:24px 0;">
    <tr>
        <td style="border-radius:4px;background-color:#1a73e8;padding:12px 32px;">
            <a href="{reset_link}" style="color:#ffffff;font-size:16px;font-weight:600;text-decoration:none;display:inline-block;">Reset Password</a>
        </td>
    </tr>
</table>
<p style="margin:16px 0 0;font-size:13px;color:#666666;">If you did not request a password reset, please ignore this email. Your password will remain unchanged.</p>
<p style="margin:8px 0 0;font-size:13px;color:#666666;">If the button above does not work, copy and paste this URL into your browser:</p>
<p style="margin:4px 0 0;font-size:13px;word-break:break-all;color:#1a73e8;">{reset_link}</p>"#,
        reset_link = reset_link
    )
}

/// Build the HTML content for an email verification.
fn build_verification_content(token: &str) -> String {
    let verify_link = format!("{}/verify-email?token={}", public_base_url(), token);
    format!(
        r#"<h2 style="margin:0 0 16px;font-size:20px;color:#1a73e8;">Verify Your Email Address</h2>
<p style="margin:0 0 16px;">Thank you for creating a Sensei OS account. Please verify your email address to activate your account.</p>
<p style="margin:0 0 16px;">Click the button below to verify your email. This link expires in <strong>24 hours</strong>.</p>
<table role="presentation" cellpadding="0" cellspacing="0" style="margin:24px 0;">
    <tr>
        <td style="border-radius:4px;background-color:#1a73e8;padding:12px 32px;">
            <a href="{verify_link}" style="color:#ffffff;font-size:16px;font-weight:600;text-decoration:none;display:inline-block;">Verify Email</a>
        </td>
    </tr>
</table>
<p style="margin:16px 0 0;font-size:13px;color:#666666;">If you did not create an account, please ignore this email.</p>
<p style="margin:8px 0 0;font-size:13px;color:#666666;">If the button above does not work, copy and paste this URL into your browser:</p>
<p style="margin:4px 0 0;font-size:13px;word-break:break-all;color:#1a73e8;">{verify_link}</p>"#,
        verify_link = verify_link
    )
}

/// Build the HTML content for a welcome email.
fn build_welcome_content(name: &str) -> String {
    format!(
        r#"<h2 style="margin:0 0 16px;font-size:20px;color:#1a73e8;">Welcome to Sensei OS, {name}!</h2>
<p style="margin:0 0 16px;">Your account has been successfully created. We're excited to have you on board!</p>
<p style="margin:0 0 16px;">With Sensei OS you can:</p>
<ul style="margin:0 0 16px;padding-left:20px;line-height:1.8;">
    <li>Manage quality processes (NCRs, CAPAs, inspections)</li>
    <li>Track production and work orders</li>
    <li>Monitor key performance indicators</li>
    <li>Collaborate with your team in real time</li>
</ul>
<p style="margin:16px 0 0;">To get started, log in to your account and complete your profile.</p>
<table role="presentation" cellpadding="0" cellspacing="0" style="margin:24px 0;">
    <tr>
        <td style="border-radius:4px;background-color:#1a73e8;padding:12px 32px;">
            <a href="{login_url}" style="color:#ffffff;font-size:16px;font-weight:600;text-decoration:none;display:inline-block;">Log In Now</a>
        </td>
    </tr>
</table>"#,
        name = name,
        login_url = format_args!("{}/login", public_base_url()),
    )
}

/// Build the HTML content for a daily digest.
fn build_digest_content(digest_html: &str) -> String {
    format!(
        r#"<h2 style="margin:0 0 16px;font-size:20px;color:#1a73e8;">Your Daily Digest</h2>
<p style="margin:0 0 16px;">Here is a summary of recent activity in your Sensei OS workspace.</p>
<div style="margin:16px 0;">{digest_html}</div>"#,
        digest_html = digest_html
    )
}

/// Build the plain text fallback for a password reset email.
fn build_password_reset_plain(token: &str) -> String {
    let reset_link = format!("{}/reset-password?token={}", public_base_url(), token);
    format!(
        "Password Reset Request\n\
         \n\
         We received a request to reset your password for your Sensei OS account.\n\
         \n\
         To reset your password, visit the following link (expires in 1 hour):\n\
         {reset_link}\n\
         \n\
         If you did not request a password reset, please ignore this email.",
        reset_link = reset_link
    )
}

/// Build the plain text fallback for an email verification.
fn build_verification_plain(token: &str) -> String {
    let verify_link = format!("{}/verify-email?token={}", public_base_url(), token);
    format!(
        "Verify Your Email Address\n\
         \n\
         Thank you for creating a Sensei OS account.\n\
         \n\
         To verify your email, visit the following link (expires in 24 hours):\n\
         {verify_link}\n\
         \n\
         If you did not create an account, please ignore this email.",
        verify_link = verify_link
    )
}

/// Build the plain text fallback for a welcome email.
fn build_welcome_plain(name: &str) -> String {
    let login_url = format!("{}/login", public_base_url());
    format!(
        "Welcome to Sensei OS, {name}!\n\
         \n\
         Your account has been successfully created.\n\
         \n\
         Log in to get started: {login_url}\n",
        name = name,
        login_url = login_url,
    )
}

// ---------------------------------------------------------------------------
// LettreEmailService — Production SMTP Implementation
// ---------------------------------------------------------------------------

/// Production email service that sends emails via SMTP using the `lettre` crate.
pub struct LettreEmailService {
    /// SMTP host address.
    smtp_host: String,
    /// SMTP port number.
    smtp_port: u16,
    /// SMTP authentication username.
    smtp_username: String,
    /// SMTP authentication password.
    smtp_password: String,
    /// From email address.
    from_address: String,
    /// From display name.
    from_name: String,
    /// Whether to use TLS encryption.
    use_tls: bool,
}

impl LettreEmailService {
    /// Create a new [`LettreEmailService`] with the given SMTP configuration.
    pub fn new(config: &sensei_core::config::EmailConfig) -> Self {
        Self {
            smtp_host: config.smtp_host.clone(),
            smtp_port: config.smtp_port,
            smtp_username: config.smtp_username.clone(),
            smtp_password: config.smtp_password.clone(),
            from_address: config.from_address.clone(),
            from_name: config.from_name.clone(),
            use_tls: config.use_tls,
        }
    }

    /// Build and send an email via SMTP.
    ///
    /// Constructs a [`lettre::Message`] with the given parameters and
    /// sends it through the configured SMTP transport.
    async fn send_email(
        &self,
        to: &str,
        subject: &str,
        html_body: &str,
        plain_body: &str,
    ) -> Result<(), SenseiError> {
        use lettre::message::header::ContentType;
        use lettre::transport::smtp::authentication::Credentials;
        use lettre::{AsyncSmtpTransport, AsyncTransport, Message, Tokio1Executor};

        let from_header = format!("{} <{}>", self.from_name, self.from_address);

        let email = Message::builder()
            .from(
                from_header
                    .parse()
                    .map_err(|e: lettre::address::AddressError| {
                        SenseiError::ExternalService(format!("Invalid from address: {e}"))
                    })?,
            )
            .to(to.parse().map_err(|e: lettre::address::AddressError| {
                SenseiError::ExternalService(format!("Invalid recipient address '{to}': {e}"))
            })?)
            .subject(subject.to_string())
            .multipart(
                lettre::message::MultiPart::alternative()
                    .singlepart(lettre::message::SinglePart::plain(plain_body.to_string()))
                    .singlepart(
                        lettre::message::SinglePart::builder()
                            .header(ContentType::TEXT_HTML)
                            .body(html_body.to_string()),
                    ),
            )
            .map_err(|e| SenseiError::ExternalService(format!("Failed to build email: {e}")))?;

        let creds = Credentials::new(self.smtp_username.clone(), self.smtp_password.clone());

        let transport = if self.use_tls {
            AsyncSmtpTransport::<Tokio1Executor>::starttls_relay(&self.smtp_host)
                .map_err(|e| SenseiError::ExternalService(format!("SMTP relay error: {e}")))?
                .port(self.smtp_port)
                .credentials(creds)
                .build()
        } else {
            AsyncSmtpTransport::<Tokio1Executor>::builder_dangerous(&self.smtp_host)
                .port(self.smtp_port)
                .credentials(creds)
                .build()
        };

        tracing::debug!(
            to = %to,
            subject = %subject,
            smtp_host = %self.smtp_host,
            smtp_port = %self.smtp_port,
            "Sending email via SMTP"
        );

        transport
            .send(email)
            .await
            .map_err(|e| SenseiError::ExternalService(format!("Failed to send email: {e}")))?;

        tracing::info!(
            to = %to,
            subject = %subject,
            "Email sent successfully via SMTP"
        );

        Ok(())
    }
}

#[async_trait]
impl EmailService for LettreEmailService {
    async fn send_password_reset(
        &self,
        email: &str,
        token: &str,
        _tenant_id: EntityId,
    ) -> Result<(), SenseiError> {
        let subject = "Password Reset Request — Sensei OS";
        let content = build_password_reset_content(token);
        let html = build_html_email(subject, &content);
        let plain = build_password_reset_plain(token);
        self.send_email(email, subject, &html, &plain).await
    }

    async fn send_email_verification(
        &self,
        email: &str,
        token: &str,
        _tenant_id: EntityId,
    ) -> Result<(), SenseiError> {
        let subject = "Verify Your Email Address — Sensei OS";
        let content = build_verification_content(token);
        let html = build_html_email(subject, &content);
        let plain = build_verification_plain(token);
        self.send_email(email, subject, &html, &plain).await
    }

    async fn send_welcome_email(
        &self,
        email: &str,
        name: &str,
        _tenant_id: EntityId,
    ) -> Result<(), SenseiError> {
        let subject = "Welcome to Sensei OS!";
        let content = build_welcome_content(name);
        let html = build_html_email(subject, &content);
        let plain = build_welcome_plain(name);
        self.send_email(email, subject, &html, &plain).await
    }

    async fn send_notification(
        &self,
        to: &str,
        subject: &str,
        body: &str,
    ) -> Result<(), SenseiError> {
        let html = build_html_email(subject, body);
        let plain = body.to_string();
        self.send_email(to, subject, &html, &plain).await
    }

    async fn send_daily_digest(&self, email: &str, digest_html: &str) -> Result<(), SenseiError> {
        let subject = "Your Daily Digest — Sensei OS";
        let content = build_digest_content(digest_html);
        let html = build_html_email(subject, &content);
        let plain = format!(
            "Your Daily Digest — Sensei OS\n\n{}",
            strip_html_tags(digest_html)
        );
        self.send_email(email, subject, &html, &plain).await
    }
}

/// Very simple HTML tag stripper for plain-text fallback generation.
fn strip_html_tags(html: &str) -> String {
    let mut result = String::with_capacity(html.len());
    let mut in_tag = false;
    for ch in html.chars() {
        match ch {
            '<' => in_tag = true,
            '>' => in_tag = false,
            _ => {
                if !in_tag {
                    result.push(ch);
                }
            }
        }
    }
    // Collapse multiple whitespace
    let mut cleaned = String::with_capacity(result.len());
    let mut prev_space = false;
    for ch in result.chars() {
        if ch.is_whitespace() {
            if !prev_space {
                cleaned.push(' ');
                prev_space = true;
            }
        } else {
            cleaned.push(ch);
            prev_space = false;
        }
    }
    cleaned.trim().to_string()
}

// ---------------------------------------------------------------------------
// InMemoryEmailService — Development / Test Implementation
// ---------------------------------------------------------------------------

/// In-memory email service for development and testing.
///
/// Stores all sent emails in an [`Arc<RwLock<Vec<SentEmail>>>`] for
/// later inspection in tests. Emails are logged via [`tracing::info!`]
/// rather than actually being sent over SMTP.
#[derive(Debug, Clone)]
pub struct InMemoryEmailService {
    /// Collection of sent emails, accessible for test assertions.
    sent_emails: Arc<RwLock<Vec<SentEmail>>>,
}

impl InMemoryEmailService {
    /// Create a new empty [`InMemoryEmailService`].
    pub fn new() -> Self {
        Self {
            sent_emails: Arc::new(RwLock::new(Vec::new())),
        }
    }

    /// Returns a clone of all sent emails for test assertions.
    pub async fn get_sent_emails(&self) -> Vec<SentEmail> {
        self.sent_emails.read().await.clone()
    }

    /// Clears all stored sent emails.
    pub async fn clear(&self) {
        self.sent_emails.write().await.clear();
    }

    /// Record a sent email for later inspection.
    async fn record_email(
        &self,
        to: String,
        subject: String,
        body: String,
        tenant_id: EntityId,
        email_type: EmailType,
    ) {
        let email = SentEmail {
            to: to.clone(),
            subject: subject.clone(),
            body,
            tenant_id,
            email_type,
        };
        self.sent_emails.write().await.push(email);
        tracing::info!(
            to = %to,
            subject = %subject,
            email_type = ?email_type,
            "Email recorded (in-memory, not actually sent)"
        );
    }
}

impl Default for InMemoryEmailService {
    fn default() -> Self {
        Self::new()
    }
}

#[async_trait]
impl EmailService for InMemoryEmailService {
    async fn send_password_reset(
        &self,
        email: &str,
        token: &str,
        tenant_id: EntityId,
    ) -> Result<(), SenseiError> {
        let subject = "Password Reset Request — Sensei OS".to_string();
        let content = build_password_reset_content(token);
        let html = build_html_email(&subject, &content);
        self.record_email(
            email.to_string(),
            subject,
            html,
            tenant_id,
            EmailType::PasswordReset,
        )
        .await;
        Ok(())
    }

    async fn send_email_verification(
        &self,
        email: &str,
        token: &str,
        tenant_id: EntityId,
    ) -> Result<(), SenseiError> {
        let subject = "Verify Your Email Address — Sensei OS".to_string();
        let content = build_verification_content(token);
        let html = build_html_email(&subject, &content);
        self.record_email(
            email.to_string(),
            subject,
            html,
            tenant_id,
            EmailType::EmailVerification,
        )
        .await;
        Ok(())
    }

    async fn send_welcome_email(
        &self,
        email: &str,
        name: &str,
        tenant_id: EntityId,
    ) -> Result<(), SenseiError> {
        let subject = "Welcome to Sensei OS!".to_string();
        let content = build_welcome_content(name);
        let html = build_html_email(&subject, &content);
        self.record_email(
            email.to_string(),
            subject,
            html,
            tenant_id,
            EmailType::Welcome,
        )
        .await;
        Ok(())
    }

    async fn send_notification(
        &self,
        to: &str,
        subject: &str,
        body: &str,
    ) -> Result<(), SenseiError> {
        let html = build_html_email(subject, body);
        // Use a nil UUID for tenant_id in generic notifications
        let tenant_id = EntityId::nil();
        self.record_email(
            to.to_string(),
            subject.to_string(),
            html,
            tenant_id,
            EmailType::Notification,
        )
        .await;
        Ok(())
    }

    async fn send_daily_digest(&self, email: &str, digest_html: &str) -> Result<(), SenseiError> {
        let subject = "Your Daily Digest — Sensei OS".to_string();
        let content = build_digest_content(digest_html);
        let html = build_html_email(&subject, &content);
        let tenant_id = EntityId::nil();
        self.record_email(
            email.to_string(),
            subject,
            html,
            tenant_id,
            EmailType::DailyDigest,
        )
        .await;
        Ok(())
    }
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_in_memory_email_service() {
        let svc = InMemoryEmailService::new();
        let tenant_id = EntityId::new_v4();

        // Send a password reset email
        svc.send_password_reset("user@test.com", "reset-token-123", tenant_id)
            .await
            .unwrap();

        let sent = svc.get_sent_emails().await;
        assert_eq!(sent.len(), 1);
        assert_eq!(sent[0].to, "user@test.com");
        assert!(sent[0].subject.contains("Password Reset"));
        assert_eq!(sent[0].email_type, EmailType::PasswordReset);
        assert!(sent[0].body.contains("reset-token-123"));
        assert!(sent[0].body.contains("Reset Password"));
        assert!(sent[0].body.contains("</html>"));

        // Send an email verification
        svc.send_email_verification("user@test.com", "verify-token-456", tenant_id)
            .await
            .unwrap();

        let sent = svc.get_sent_emails().await;
        assert_eq!(sent.len(), 2);
        assert_eq!(sent[1].email_type, EmailType::EmailVerification);
        assert!(sent[1].body.contains("verify-token-456"));
        assert!(sent[1].body.contains("Verify Email"));

        // Send a welcome email
        svc.send_welcome_email("newuser@test.com", "John Doe", tenant_id)
            .await
            .unwrap();

        let sent = svc.get_sent_emails().await;
        assert_eq!(sent.len(), 3);
        assert!(sent[2].subject.contains("Welcome"));
        assert!(sent[2].body.contains("John Doe"));

        // Send a notification
        svc.send_notification("notify@test.com", "Test Subject", "Test body")
            .await
            .unwrap();

        let sent = svc.get_sent_emails().await;
        assert_eq!(sent.len(), 4);
        assert_eq!(sent[3].subject, "Test Subject");

        // Send a daily digest
        svc.send_daily_digest(
            "digest@test.com",
            "<p>3 new NCRs</p><p>2 completed work orders</p>",
        )
        .await
        .unwrap();

        let sent = svc.get_sent_emails().await;
        assert_eq!(sent.len(), 5);
        assert!(sent[4].subject.contains("Daily Digest"));
        assert!(sent[4].body.contains("3 new NCRs"));

        // Test clear
        svc.clear().await;
        let sent = svc.get_sent_emails().await;
        assert!(sent.is_empty());
    }

    #[test]
    fn test_strip_html_tags() {
        let html = "<p>Hello <b>World</b></p>";
        assert_eq!(strip_html_tags(html), "Hello World");
    }

    #[test]
    fn test_build_html_email_wraps_content() {
        let html = build_html_email("Test", "<p>Content</p>");
        assert!(html.starts_with("<!DOCTYPE html>"));
        assert!(html.contains("Sensei OS"));
        assert!(html.contains("<p>Content</p>"));
        assert!(html.contains("</html>"));
    }

    #[test]
    fn test_password_reset_content_has_absolute_link() {
        // Explicit value: parallel tests mutate PUBLIC_BASE_URL, so the
        // process default cannot be asserted race-free.
        std::env::set_var("PUBLIC_BASE_URL", "http://localhost:3000/");
        let content = build_password_reset_content("abc-123");
        assert!(content.contains("http://localhost:3000/reset-password?token=abc-123"));
        assert!(
            !content.contains("href=\"/reset-password"),
            "link must be absolute: {content}"
        );
        assert!(content.contains("Reset Password"));
        assert!(content.contains("1 hour"));

        // The env override is honoured and trailing slashes are trimmed.
        std::env::set_var("PUBLIC_BASE_URL", "https://sensei.example.com/");
        let content = build_password_reset_content("abc-123");
        assert!(content.contains("https://sensei.example.com/reset-password?token=abc-123"));
        std::env::remove_var("PUBLIC_BASE_URL");
    }

    #[test]
    fn test_verification_content_has_absolute_link() {
        // Explicit value: parallel tests mutate PUBLIC_BASE_URL, so the
        // process default cannot be asserted race-free.
        std::env::set_var("PUBLIC_BASE_URL", "http://localhost:3000/");
        let content = build_verification_content("xyz-789");
        assert!(content.contains("http://localhost:3000/verify-email?token=xyz-789"));
        assert!(
            !content.contains("href=\"/verify-email"),
            "link must be absolute: {content}"
        );
        assert!(content.contains("Verify Email"));
        assert!(content.contains("24 hours"));
    }

    #[test]
    fn test_plain_text_fallbacks_use_absolute_links() {
        // Use an explicit base URL: tests run in parallel and mutate the
        // process environment, so asserting the DEFAULT value would race
        // with other tests that override PUBLIC_BASE_URL.
        std::env::set_var("PUBLIC_BASE_URL", "http://localhost:3000/");
        let reset_plain = build_password_reset_plain("tok-1");
        assert!(reset_plain.contains("http://localhost:3000/reset-password?token=tok-1"));
        let verify_plain = build_verification_plain("tok-2");
        assert!(verify_plain.contains("http://localhost:3000/verify-email?token=tok-2"));
        let welcome_plain = build_welcome_plain("Alice");
        assert!(welcome_plain.contains("http://localhost:3000/login"));
        std::env::remove_var("PUBLIC_BASE_URL");
    }

    #[test]
    fn test_welcome_content_has_name() {
        let content = build_welcome_content("Alice");
        assert!(content.contains("Alice"));
        assert!(content.contains("Log In Now"));
    }
}
