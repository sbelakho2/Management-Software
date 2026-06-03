//! Notification services for the Sensei ERP system.
//!
//! Provides email sending capabilities via SMTP (production) or
//! in-memory storage (development/testing), as well as in-app
//! notification delivery with database persistence and preference
//! management.

pub mod email;
pub mod service;

pub use email::EmailService;
pub use email::InMemoryEmailService;
pub use email::LettreEmailService;
pub use email::SentEmail;
pub use service::{
    DatabaseNotificationService, InMemoryNotificationService, Notification,
    NotificationPreferences, NotificationService,
};
