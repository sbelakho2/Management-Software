//! Human resources models for compensation, training programs, and enrollments.

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use uuid::Uuid;

/// Database representation of employee compensation.
///
/// Compensation records track salary history, pay frequency, and
/// benefits for employees with effective date tracking.
#[derive(Debug, Clone, sqlx::FromRow, Serialize, Deserialize)]
pub struct EmployeeCompensationModel {
    /// Primary key (UUID).
    pub id: Uuid,
    /// Tenant foreign key.
    pub tenant_id: Uuid,
    /// Employee reference.
    pub employee_id: Uuid,
    /// Base salary amount.
    pub base_salary: f64,
    /// Currency code.
    pub currency: String,
    /// Pay frequency (hourly, weekly, bi_weekly, monthly, annual).
    pub pay_frequency: String,
    /// Effective date of this compensation.
    pub effective_date: DateTime<Utc>,
    /// End date (null if current).
    pub end_date: Option<DateTime<Utc>>,
    /// Next review date.
    pub review_date: Option<DateTime<Utc>>,
    /// Whether eligible for bonus.
    pub bonus_eligible: bool,
    /// Bonus target percentage.
    pub bonus_target: Option<f64>,
    /// Value of benefits package.
    pub benefits_value: f64,
    /// Notes.
    pub notes: Option<String>,
    /// User who created the record.
    pub created_by: Option<Uuid>,
    /// Record creation timestamp.
    pub created_at: DateTime<Utc>,
    /// Record last update timestamp.
    pub updated_at: DateTime<Utc>,
}

/// Database representation of a training program.
///
/// Training programs define available courses with delivery method,
/// duration, and certification requirements.
#[derive(Debug, Clone, sqlx::FromRow, Serialize, Deserialize)]
pub struct TrainingProgramModel {
    /// Primary key (UUID).
    pub id: Uuid,
    /// Tenant foreign key.
    pub tenant_id: Uuid,
    /// Human-readable program code.
    pub program_code: String,
    /// Program name.
    pub name: String,
    /// Description.
    pub description: Option<String>,
    /// Duration in hours.
    pub duration_hours: f64,
    /// Category.
    pub category: Option<String>,
    /// Delivery method (classroom, online, on_the_job, blended, self_paced).
    pub delivery_method: String,
    /// Status (draft, active, inactive, archived).
    pub status: String,
    /// Whether certification is awarded.
    pub certification_required: bool,
    /// Certification validity period in months.
    pub certification_validity: Option<i32>,
    /// Whether recertification is required.
    pub recertification_required: bool,
    /// Maximum participants per session.
    pub max_participants: Option<i32>,
    /// Trainer user ID.
    pub trainer_id: Option<Uuid>,
    /// Training materials reference.
    pub materials: Option<String>,
    /// Record creation timestamp.
    pub created_at: DateTime<Utc>,
    /// Record last update timestamp.
    pub updated_at: DateTime<Utc>,
}

/// Database representation of a training enrollment.
///
/// Enrollments track employee participation in training programs,
/// including progress, scores, and certification.
#[derive(Debug, Clone, sqlx::FromRow, Serialize, Deserialize)]
pub struct TrainingEnrollmentModel {
    /// Primary key (UUID).
    pub id: Uuid,
    /// Tenant foreign key.
    pub tenant_id: Uuid,
    /// Training program.
    pub program_id: Uuid,
    /// Enrolled employee.
    pub employee_id: Uuid,
    /// Status (enrolled, in_progress, completed, failed, cancelled, expired).
    pub status: String,
    /// Enrollment timestamp.
    pub enrolled_at: DateTime<Utc>,
    /// Start timestamp.
    pub started_at: Option<DateTime<Utc>>,
    /// Completion timestamp.
    pub completed_at: Option<DateTime<Utc>>,
    /// Score achieved.
    pub score: Option<f64>,
    /// Whether the employee passed.
    pub passed: bool,
    /// Certificate number awarded.
    pub certificate_number: Option<String>,
    /// Notes.
    pub notes: Option<String>,
    /// Record creation timestamp.
    pub created_at: DateTime<Utc>,
    /// Record last update timestamp.
    pub updated_at: DateTime<Utc>,
}
