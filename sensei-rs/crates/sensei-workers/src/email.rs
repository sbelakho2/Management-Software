//! Email worker — replaces Celery's `send_email_task`.
//!
//! Listens on `sensei.tasks.email.send` and dispatches emails via SMTP
//! using the `lettre` crate. SMTP configuration is read from environment
//! variables at worker construction time. If SMTP is not configured, the
//! worker logs a warning and gracefully degrades (skips sending).

use crate::error::{Result, WorkerError};
use crate::task::{IdempotencyGuard, TaskConsumer, TaskMetadata, TaskOutcome};
use async_trait::async_trait;
use lettre::message::header::ContentType;
use lettre::message::Mailbox;
use lettre::transport::smtp::authentication::Credentials;
use lettre::{AsyncSmtpTransport, AsyncTransport, Message, Tokio1Executor};
use serde::{Deserialize, Serialize};
use sqlx::PgPool;
use std::str::FromStr;
use std::sync::Arc;
use tracing::{error, info, warn};

/// Payload for the email send task.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EmailTaskPayload {
    /// Recipient addresses.
    pub to: Vec<String>,
    /// Email subject line.
    pub subject: String,
    /// HTML body content.
    pub body_html: String,
    /// Optional plain-text fallback body.
    pub body_text: Option<String>,
    /// Optional reply-to address.
    pub reply_to: Option<String>,
    /// CC recipients.
    #[serde(default)]
    pub cc: Vec<String>,
    /// BCC recipients.
    #[serde(default)]
    pub bcc: Vec<String>,
}

/// SMTP configuration populated from environment variables.
///
/// | Variable     | Default          | Description                    |
/// |--------------|------------------|--------------------------------|
/// | `SMTP_HOST`  | — (required)     | SMTP relay hostname            |
/// | `SMTP_PORT`  | `587`            | SMTP port                      |
/// | `SMTP_USER`  | — (required)     | Authentication username        |
/// | `SMTP_PASS`  | — (required)     | Authentication password        |
/// | `SMTP_FROM`  | `noreply@sensei` | Default From address           |
#[derive(Debug, Clone)]
pub struct SmtpConfig {
    /// SMTP host.
    pub host: String,
    /// SMTP port.
    pub port: u16,
    /// Username for authentication.
    pub username: String,
    /// Password for authentication.
    pub password: String,
    /// Default From address.
    pub from_address: String,
    /// Whether TLS is enabled.
    pub use_tls: bool,
}

impl SmtpConfig {
    /// Read SMTP configuration from environment variables.
    ///
    /// Returns `None` (and logs a warning) if `SMTP_HOST` is not set,
    /// indicating that SMTP is not configured.
    pub fn from_env() -> Option<Self> {
        let host = std::env::var("SMTP_HOST").ok();
        if host.as_ref().map(|h| h.is_empty()).unwrap_or(true) {
            warn!(
                "SMTP_HOST not set — email sending is disabled. \
                 Set SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS, SMTP_FROM to enable."
            );
            return None;
        }

        Some(Self {
            host: host.unwrap(),
            port: std::env::var("SMTP_PORT")
                .ok()
                .and_then(|p| p.parse().ok())
                .unwrap_or(587),
            username: std::env::var("SMTP_USER").unwrap_or_default(),
            password: std::env::var("SMTP_PASS").unwrap_or_default(),
            from_address: std::env::var("SMTP_FROM")
                .unwrap_or_else(|_| "noreply@sensei-erp.com".to_string()),
            use_tls: true,
        })
    }
}

impl Default for SmtpConfig {
    fn default() -> Self {
        Self {
            host: String::new(),
            port: 587,
            username: String::new(),
            password: String::new(),
            from_address: "noreply@sensei-erp.com".to_string(),
            use_tls: false,
        }
    }
}

/// Worker that processes email-send tasks.
///
/// Uses `lettre::AsyncSmtpTransport` to deliver emails via SMTP. SMTP
/// availability is validated at startup: when the SMTP configuration is
/// missing, the worker logs a prominent error once and every email task
/// fails permanently (so the dispatcher dead-letters it instead of silently
/// dropping the email).
pub struct EmailWorker {
    /// SMTP configuration.
    pub config: SmtpConfig,
    /// Whether SMTP is fully configured and ready to send.
    smtp_available: bool,
    /// Idempotency guard (migration 053): claims the task_id before sending
    /// so a redelivered message never sends the same email twice.
    idempotency: IdempotencyGuard,
}

impl EmailWorker {
    /// Create a new [`EmailWorker`] by reading SMTP config from environment.
    ///
    /// If SMTP env vars are not set, the worker logs a prominent startup
    /// error; email tasks then fail permanently and are dead-lettered.
    pub fn new() -> Self {
        Self::with_pool(None)
    }

    /// Create an [`EmailWorker`] with a database pool for task idempotency.
    pub fn with_pool(pool: Option<Arc<PgPool>>) -> Self {
        let config = SmtpConfig::from_env();
        match config {
            Some(cfg) => Self {
                smtp_available: true,
                config: cfg,
                idempotency: IdempotencyGuard::new(pool, "email"),
            },
            None => {
                error!(
                    "SMTP is NOT configured (SMTP_HOST is unset). Every email task will fail \
                     permanently and be dead-lettered. Set SMTP_HOST, SMTP_PORT, SMTP_USER, \
                     SMTP_PASS, SMTP_FROM to enable email delivery."
                );
                Self {
                    smtp_available: false,
                    config: SmtpConfig::default(),
                    idempotency: IdempotencyGuard::new(pool, "email"),
                }
            }
        }
    }

    /// Create an [`EmailWorker`] with a custom SMTP config.
    pub fn with_config(config: SmtpConfig) -> Self {
        let smtp_available = !config.host.is_empty();
        if !smtp_available {
            error!(
                "SMTP is NOT configured (empty SMTP host). Every email task will fail \
                 permanently and be dead-lettered."
            );
        }
        Self {
            smtp_available,
            config,
            idempotency: IdempotencyGuard::new(None, "email"),
        }
    }

    /// Build the SMTP transport from the current configuration.
    fn build_transport(&self) -> Result<AsyncSmtpTransport<Tokio1Executor>> {
        let creds = Credentials::new(self.config.username.clone(), self.config.password.clone());

        // Use STARTTLS for all connections. For local dev (MailHog/Mailpit),
        // STARTTLS will be negotiated but TLS won't be enforced.
        let transport = AsyncSmtpTransport::<Tokio1Executor>::starttls_relay(&self.config.host)
            .map_err(|e| {
                WorkerError::Processing(format!(
                    "Failed to create STARTTLS transport for {}: {}",
                    self.config.host, e
                ))
            })?
            .credentials(creds)
            .port(self.config.port)
            .build();

        Ok(transport)
    }

    /// Send an email via SMTP.
    ///
    /// If SMTP is not configured, logs a warning and returns `Ok(())` (graceful
    /// degradation). On transient SMTP errors, returns
    /// [`WorkerError::RetryLater`] so the dispatcher can retry.
    async fn send_email(&self, payload: &EmailTaskPayload) -> Result<()> {
        // Validate that at least one recipient exists.
        if payload.to.is_empty() {
            return Err(WorkerError::Processing(
                "Email must have at least one 'to' recipient".to_string(),
            ));
        }

        // No graceful degradation: when SMTP is not configured the task fails
        // permanently so the dispatcher dead-letters it and the operator can
        // see the failure instead of silently losing the email.
        if !self.smtp_available {
            return Err(WorkerError::Processing(
                "SMTP is not configured (SMTP_HOST is unset) — email delivery is unavailable"
                    .to_string(),
            ));
        }

        // Build the From mailbox.
        let from = Mailbox::from_str(&self.config.from_address).map_err(|e| {
            WorkerError::Processing(format!(
                "Invalid SMTP_FROM address '{}': {}",
                self.config.from_address, e
            ))
        })?;

        // Build the email message.
        let mut builder = Message::builder().from(from).subject(&payload.subject);

        // Add To recipients.
        for addr in &payload.to {
            let mailbox = Mailbox::from_str(addr).map_err(|e| {
                WorkerError::Processing(format!("Invalid 'to' address '{}': {}", addr, e))
            })?;
            builder = builder.to(mailbox);
        }

        // Add CC recipients.
        for addr in &payload.cc {
            let mailbox = Mailbox::from_str(addr).map_err(|e| {
                WorkerError::Processing(format!("Invalid 'cc' address '{}': {}", addr, e))
            })?;
            builder = builder.cc(mailbox);
        }

        // Add BCC recipients.
        for addr in &payload.bcc {
            let mailbox = Mailbox::from_str(addr).map_err(|e| {
                WorkerError::Processing(format!("Invalid 'bcc' address '{}': {}", addr, e))
            })?;
            builder = builder.bcc(mailbox);
        }

        // Add Reply-To if specified.
        if let Some(ref reply_to) = payload.reply_to {
            let mailbox = Mailbox::from_str(reply_to).map_err(|e| {
                WorkerError::Processing(format!("Invalid 'reply_to' address '{}': {}", reply_to, e))
            })?;
            builder = builder.reply_to(mailbox);
        }

        // Build the email message.
        let email = if payload.body_text.is_some() {
            // Multipart: plain-text + HTML alternative.
            builder
                .multipart(
                    lettre::message::MultiPart::alternative()
                        .singlepart(
                            lettre::message::SinglePart::builder()
                                .header(ContentType::TEXT_PLAIN)
                                .body(payload.body_text.clone().unwrap()),
                        )
                        .singlepart(
                            lettre::message::SinglePart::builder()
                                .header(ContentType::TEXT_HTML)
                                .body(payload.body_html.clone()),
                        ),
                )
                .map_err(|e| {
                    WorkerError::Processing(format!("Failed to build email message: {}", e))
                })?
        } else {
            // HTML-only body.
            builder
                .header(ContentType::TEXT_HTML)
                .body(payload.body_html.clone())
                .map_err(|e| {
                    WorkerError::Processing(format!("Failed to build email message: {}", e))
                })?
        };

        // Build the transport and send.
        let transport = self.build_transport()?;
        match transport.send(email).await {
            Ok(response) => {
                info!(
                    to = ?payload.to,
                    cc = ?payload.cc,
                    bcc_count = payload.bcc.len(),
                    subject = %payload.subject,
                    response = ?response,
                    "Email dispatched successfully via SMTP"
                );
                Ok(())
            }
            Err(e) => {
                let err_msg = format!("SMTP delivery failed: {}", e);
                error!(
                    to = ?payload.to,
                    subject = %payload.subject,
                    error = %e,
                    "SMTP delivery failed"
                );
                // Transient errors (connection, timeout) should be retried.
                Err(WorkerError::RetryLater(err_msg))
            }
        }
    }
}

impl Default for EmailWorker {
    fn default() -> Self {
        Self::new()
    }
}

#[async_trait]
impl TaskConsumer for EmailWorker {
    fn subject(&self) -> &'static str {
        "sensei.tasks.email.send"
    }

    fn consumer_group(&self) -> &'static str {
        "sensei-workers-email"
    }

    async fn process(&self, payload: &[u8], metadata: &TaskMetadata) -> Result<TaskOutcome> {
        let email_payload: EmailTaskPayload = serde_json::from_slice(payload).map_err(|e| {
            error!(
                task_id = %metadata.task_id,
                error = %e,
                "Failed to deserialize email task payload"
            );
            WorkerError::Serialization(e)
        })?;

        // Idempotency: claim the task_id BEFORE the side effect (SMTP send).
        // A redelivered message is skipped, never re-sent.
        let task_id_str = metadata.task_id.to_string();
        match self.idempotency.try_claim(&task_id_str).await {
            Ok(true) => {}
            Ok(false) => {
                info!(
                    task_id = %metadata.task_id,
                    "Email task already processed — skipping (idempotent)"
                );
                return Ok(TaskOutcome::Completed);
            }
            Err(e) => {
                return Err(WorkerError::RetryLater(format!(
                    "idempotency claim failed for email task: {e}"
                )));
            }
        }

        crate::task::outcome_from_result(self.send_email(&email_payload).await).inspect(|outcome| {
            if *outcome == TaskOutcome::Completed {
                info!(
                    task_id = %metadata.task_id,
                    to = ?email_payload.to,
                    subject = %email_payload.subject,
                    "Email task completed"
                );
            } else {
                error!(
                    task_id = %metadata.task_id,
                    to = ?email_payload.to,
                    subject = %email_payload.subject,
                    "Email task failed"
                );
            }
        })
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_email_payload_serialization() {
        let payload = EmailTaskPayload {
            to: vec!["user@example.com".to_string()],
            subject: "Test".to_string(),
            body_html: "<h1>Test</h1>".to_string(),
            body_text: Some("Test".to_string()),
            reply_to: None,
            cc: vec![],
            bcc: vec![],
        };

        let json = serde_json::to_string(&payload).unwrap();
        let deserialized: EmailTaskPayload = serde_json::from_str(&json).unwrap();
        assert_eq!(deserialized.to, payload.to);
        assert_eq!(deserialized.subject, payload.subject);
    }

    #[test]
    fn test_email_payload_empty_to_fails() {
        let payload = EmailTaskPayload {
            to: vec![],
            subject: "Test".to_string(),
            body_html: "<h1>Test</h1>".to_string(),
            body_text: None,
            reply_to: None,
            cc: vec![],
            bcc: vec![],
        };

        let worker = EmailWorker::with_config(SmtpConfig::default());
        let rt = tokio::runtime::Runtime::new().unwrap();
        let result = rt.block_on(worker.send_email(&payload));
        assert!(result.is_err());
    }

    #[test]
    fn test_smtp_config_from_env_missing() {
        // Ensure SMTP_HOST is not set for this test.
        std::env::remove_var("SMTP_HOST");
        assert!(SmtpConfig::from_env().is_none());
    }

    #[test]
    fn test_missing_smtp_is_a_permanent_failure() {
        let worker = EmailWorker::with_config(SmtpConfig::default());
        assert!(!worker.smtp_available);

        let payload = EmailTaskPayload {
            to: vec!["user@example.com".to_string()],
            subject: "Test".to_string(),
            body_html: "<h1>Test</h1>".to_string(),
            body_text: None,
            reply_to: None,
            cc: vec![],
            bcc: vec![],
        };

        let rt = tokio::runtime::Runtime::new().unwrap();
        let result = rt.block_on(worker.send_email(&payload));
        // Missing SMTP must fail permanently (→ DLQ), never silently skip.
        assert!(result.is_err());
        assert!(
            !matches!(result, Err(WorkerError::RetryLater(_))),
            "missing SMTP is a permanent misconfiguration, not a transient failure"
        );
    }
}
