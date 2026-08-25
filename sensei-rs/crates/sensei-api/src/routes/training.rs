//! Training (General Training Courses) route handlers.
//!
//! Provides endpoints for managing training courses, enrollments,
//! and training dashboards. This module is separate from the
//! training-matrix module (skill matrix).

use axum::{
    extract::{Path, Query, State},
    Json,
};
use chrono::{DateTime, Utc};
use sensei_auth::middleware::AuthenticatedUser;
use sensei_core::error::{Result, SenseiError};
use sensei_core::pagination::PaginatedResponse;
use sensei_core::types::new_id;
use serde::{Deserialize, Serialize};
use uuid::Uuid;

use crate::state::AppState;
use crate::stores::{
    TrainingCategory, TrainingCourse, TrainingEnrollment, TrainingEnrollmentStatus,
};

// ── Query / Request DTOs ───────────────────────────────────────────────────

/// Query parameters for listing training courses.
#[derive(Debug, Deserialize)]
pub struct ListCoursesParams {
    pub category: Option<TrainingCategory>,
    pub is_mandatory: Option<bool>,
    pub is_active: Option<bool>,
    pub page: Option<usize>,
    pub per_page: Option<usize>,
}

/// Request body for creating/updating a training course.
#[derive(Debug, Deserialize)]
pub struct CreateCourseRequest {
    pub title: String,
    pub description: Option<String>,
    pub category: TrainingCategory,
    pub duration_minutes: i32,
    pub required_for_roles: Vec<String>,
    pub prerequisites: Vec<Uuid>,
    pub content_url: Option<String>,
    pub passing_score: Option<f64>,
    pub is_mandatory: bool,
}

/// Request body for updating a training course (partial).
#[derive(Debug, Deserialize)]
pub struct UpdateCourseRequest {
    pub title: Option<String>,
    pub description: Option<String>,
    pub category: Option<TrainingCategory>,
    pub duration_minutes: Option<i32>,
    pub required_for_roles: Option<Vec<String>>,
    pub prerequisites: Option<Vec<Uuid>>,
    pub content_url: Option<String>,
    pub passing_score: Option<f64>,
    pub is_mandatory: Option<bool>,
    pub is_active: Option<bool>,
}

/// Request body for enrolling users in a course.
#[derive(Debug, Deserialize)]
pub struct EnrollUsersRequest {
    pub user_ids: Vec<Uuid>,
    pub deadline: Option<DateTime<Utc>>,
}

/// Query parameters for listing enrollments.
#[derive(Debug, Deserialize)]
pub struct ListEnrollmentsParams {
    pub status: Option<TrainingEnrollmentStatus>,
    pub user_id: Option<Uuid>,
    pub page: Option<usize>,
    pub per_page: Option<usize>,
}

/// Request body for updating enrollment status.
#[derive(Debug, Deserialize)]
pub struct UpdateEnrollmentStatusRequest {
    pub status: TrainingEnrollmentStatus,
    pub score: Option<f64>,
}

/// Query parameters for my-courses.
#[derive(Debug, Deserialize)]
pub struct MyCoursesParams {
    pub status: Option<TrainingEnrollmentStatus>,
    pub page: Option<usize>,
    pub per_page: Option<usize>,
}

// ── Response DTOs ──────────────────────────────────────────────────────────

/// Training dashboard response.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TrainingDashboard {
    pub total_courses: usize,
    pub total_enrollments: usize,
    pub completion_rate: f64,
    pub overdue_count: usize,
    pub by_department: Vec<DepartmentTrainingSummary>,
    pub by_category: Vec<CategoryTrainingSummary>,
}

/// Training summary grouped by department/role.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DepartmentTrainingSummary {
    pub role: String,
    pub total_enrollments: usize,
    pub completed: usize,
    pub completion_rate: f64,
}

/// Training summary grouped by category.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CategoryTrainingSummary {
    pub category: TrainingCategory,
    pub total_courses: usize,
    pub total_enrollments: usize,
    pub completion_rate: f64,
}

// ── Course Handlers ────────────────────────────────────────────────────────

/// List training courses with optional filters and pagination.
pub async fn list_courses(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Query(params): Query<ListCoursesParams>,
) -> Result<Json<PaginatedResponse<TrainingCourse>>> {
    let tenant_id = user.tenant_id;
    let store = state.training_courses.read().await;
    let mut courses: Vec<TrainingCourse> = store
        .values()
        .filter(|c| c.tenant_id == tenant_id)
        .filter(|c| {
            if let Some(ref cat) = params.category {
                std::mem::discriminant(cat) == std::mem::discriminant(&c.category)
            } else {
                true
            }
        })
        .filter(|c| {
            if let Some(mandatory) = params.is_mandatory {
                c.is_mandatory == mandatory
            } else {
                true
            }
        })
        .filter(|c| {
            if let Some(active) = params.is_active {
                c.is_active == active
            } else {
                true
            }
        })
        .cloned()
        .collect();
    courses.sort_by(|a, b| a.title.cmp(&b.title));
    let result = PaginatedResponse::new(courses, params.page, params.per_page);
    Ok(Json(result))
}

/// Create a new training course.
pub async fn create_course(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Json(req): Json<CreateCourseRequest>,
) -> Result<Json<TrainingCourse>> {
    let tenant_id = user.tenant_id;
    let now = Utc::now();
    let course = TrainingCourse {
        id: new_id(),
        tenant_id,
        title: req.title,
        description: req.description,
        category: req.category,
        duration_minutes: req.duration_minutes,
        required_for_roles: req.required_for_roles,
        prerequisites: req.prerequisites,
        content_url: req.content_url,
        passing_score: req.passing_score,
        is_mandatory: req.is_mandatory,
        is_active: true,
        created_by: user.user_id,
        created_at: now,
        updated_at: now,
    };
    let mut store = state.training_courses.write().await;
    store.insert(course.id, course.clone());
    Ok(Json(course))
}

/// Get a training course by ID.
pub async fn get_course(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(course_id): Path<Uuid>,
) -> Result<Json<TrainingCourse>> {
    let tenant_id = user.tenant_id;
    let store = state.training_courses.read().await;
    let course = store
        .values()
        .find(|c| c.id == course_id && c.tenant_id == tenant_id)
        .cloned()
        .ok_or_else(|| SenseiError::NotFound(format!("Course {course_id} not found")))?;
    Ok(Json(course))
}

/// Update a training course.
pub async fn update_course(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(course_id): Path<Uuid>,
    Json(req): Json<UpdateCourseRequest>,
) -> Result<Json<TrainingCourse>> {
    let tenant_id = user.tenant_id;
    let mut store = state.training_courses.write().await;
    let course = store
        .get_mut(&course_id)
        .filter(|c| c.tenant_id == tenant_id)
        .ok_or_else(|| SenseiError::NotFound(format!("Course {course_id} not found")))?;
    if let Some(title) = req.title {
        course.title = title;
    }
    if let Some(desc) = req.description {
        course.description = Some(desc);
    }
    if let Some(cat) = req.category {
        course.category = cat;
    }
    if let Some(dur) = req.duration_minutes {
        course.duration_minutes = dur;
    }
    if let Some(roles) = req.required_for_roles {
        course.required_for_roles = roles;
    }
    if let Some(pre) = req.prerequisites {
        course.prerequisites = pre;
    }
    if let Some(url) = req.content_url {
        course.content_url = Some(url);
    }
    if let Some(score) = req.passing_score {
        course.passing_score = Some(score);
    }
    if let Some(mandatory) = req.is_mandatory {
        course.is_mandatory = mandatory;
    }
    if let Some(active) = req.is_active {
        course.is_active = active;
    }
    course.updated_at = Utc::now();
    Ok(Json(course.clone()))
}

/// Delete a training course.
pub async fn delete_course(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(course_id): Path<Uuid>,
) -> Result<Json<()>> {
    let tenant_id = user.tenant_id;
    let mut store = state.training_courses.write().await;
    let exists = store
        .get(&course_id)
        .filter(|c| c.tenant_id == tenant_id)
        .is_some();
    if !exists {
        return Err(SenseiError::NotFound(format!(
            "Course {course_id} not found"
        )));
    }
    store.remove(&course_id);
    Ok(Json(()))
}

// ── Enrollment Handlers ────────────────────────────────────────────────────

/// Enroll one or more users in a course.
///
/// Users who are already enrolled in the course are skipped (no duplicate
/// enrollments are created).
pub async fn enroll_users(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(course_id): Path<Uuid>,
    Json(req): Json<EnrollUsersRequest>,
) -> Result<Json<Vec<TrainingEnrollment>>> {
    let tenant_id = user.tenant_id;
    // Verify course exists
    {
        let store = state.training_courses.read().await;
        if !store
            .values()
            .any(|c| c.id == course_id && c.tenant_id == tenant_id)
        {
            return Err(SenseiError::NotFound(format!(
                "Course {course_id} not found"
            )));
        }
    }

    // Collect user ids that are already enrolled in this course.
    let already_enrolled: std::collections::HashSet<Uuid> = {
        let store = state.training_enrollments.read().await;
        store
            .values()
            .filter(|e| e.course_id == course_id && e.tenant_id == tenant_id)
            .map(|e| e.user_id)
            .collect()
    };

    let now = Utc::now();
    let mut enrollments = Vec::new();
    let mut enrollment_store = state.training_enrollments.write().await;

    for uid in req.user_ids {
        if already_enrolled.contains(&uid) {
            continue;
        }
        let enrollment = TrainingEnrollment {
            id: new_id(),
            course_id,
            tenant_id,
            user_id: uid,
            status: TrainingEnrollmentStatus::Enrolled,
            score: None,
            completed_at: None,
            deadline: req.deadline,
            enrolled_by: user.user_id,
            enrolled_at: now,
        };
        enrollment_store.insert(enrollment.id, enrollment.clone());
        enrollments.push(enrollment);
    }

    Ok(Json(enrollments))
}

/// List enrollments for a course.
pub async fn list_enrollments(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(course_id): Path<Uuid>,
    Query(params): Query<ListEnrollmentsParams>,
) -> Result<Json<PaginatedResponse<TrainingEnrollment>>> {
    let tenant_id = user.tenant_id;
    let store = state.training_enrollments.read().await;
    let mut enrollments: Vec<TrainingEnrollment> = store
        .values()
        .filter(|e| e.course_id == course_id && e.tenant_id == tenant_id)
        .filter(|e| {
            if let Some(ref status) = params.status {
                std::mem::discriminant(status) == std::mem::discriminant(&e.status)
            } else {
                true
            }
        })
        .filter(|e| {
            if let Some(uid) = params.user_id {
                e.user_id == uid
            } else {
                true
            }
        })
        .cloned()
        .collect();
    enrollments.sort_by_key(|a| std::cmp::Reverse(a.enrolled_at));
    let result = PaginatedResponse::new(enrollments, params.page, params.per_page);
    Ok(Json(result))
}

/// Update enrollment status (e.g., mark as completed, passed, failed).
pub async fn update_enrollment_status(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(enrollment_id): Path<Uuid>,
    Json(req): Json<UpdateEnrollmentStatusRequest>,
) -> Result<Json<TrainingEnrollment>> {
    let tenant_id = user.tenant_id;
    let mut store = state.training_enrollments.write().await;
    let enrollment = store
        .get_mut(&enrollment_id)
        .filter(|e| e.tenant_id == tenant_id)
        .ok_or_else(|| SenseiError::NotFound(format!("Enrollment {enrollment_id} not found")))?;

    enrollment.status = req.status;
    if let Some(score) = req.score {
        enrollment.score = Some(score);
    }
    if matches!(
        enrollment.status,
        TrainingEnrollmentStatus::Completed
            | TrainingEnrollmentStatus::Passed
            | TrainingEnrollmentStatus::Failed
    ) {
        enrollment.completed_at = Some(Utc::now());
    }
    Ok(Json(enrollment.clone()))
}

// ── User-Specific & Dashboard ──────────────────────────────────────────────

/// Get the current user's enrolled courses.
pub async fn my_courses(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Query(params): Query<MyCoursesParams>,
) -> Result<Json<PaginatedResponse<TrainingEnrollment>>> {
    let tenant_id = user.tenant_id;
    let store = state.training_enrollments.read().await;
    let mut enrollments: Vec<TrainingEnrollment> = store
        .values()
        .filter(|e| e.user_id == user.user_id && e.tenant_id == tenant_id)
        .filter(|e| {
            if let Some(ref status) = params.status {
                std::mem::discriminant(status) == std::mem::discriminant(&e.status)
            } else {
                true
            }
        })
        .cloned()
        .collect();
    enrollments.sort_by_key(|a| std::cmp::Reverse(a.enrolled_at));
    let result = PaginatedResponse::new(enrollments, params.page, params.per_page);
    Ok(Json(result))
}

/// Get training dashboard with completion rates, overdue, by department.
pub async fn get_training_dashboard(
    user: AuthenticatedUser,
    State(state): State<AppState>,
) -> Result<Json<TrainingDashboard>> {
    let tenant_id = user.tenant_id;

    let courses_store = state.training_courses.read().await;
    let enrollments_store = state.training_enrollments.read().await;

    let courses: Vec<&TrainingCourse> = courses_store
        .values()
        .filter(|c| c.tenant_id == tenant_id)
        .collect();
    let enrollments: Vec<&TrainingEnrollment> = enrollments_store
        .values()
        .filter(|e| e.tenant_id == tenant_id)
        .collect();

    let total_courses = courses.len();
    let total_enrollments = enrollments.len();

    let completed_count = enrollments
        .iter()
        .filter(|e| {
            matches!(
                e.status,
                TrainingEnrollmentStatus::Completed | TrainingEnrollmentStatus::Passed
            )
        })
        .count();
    let completion_rate = if total_enrollments > 0 {
        (completed_count as f64 / total_enrollments as f64) * 100.0
    } else {
        100.0
    };

    let now = Utc::now();
    let overdue_count = enrollments
        .iter()
        .filter(|e| {
            if let Some(deadline) = e.deadline {
                deadline < now
                    && !matches!(
                        e.status,
                        TrainingEnrollmentStatus::Completed
                            | TrainingEnrollmentStatus::Passed
                            | TrainingEnrollmentStatus::Failed
                    )
            } else {
                false
            }
        })
        .count();

    // By department/role: count actual enrollments whose course requires the
    // role, so `total_enrollments` and `completed` are measured consistently.
    let mut dept_map: std::collections::HashMap<String, (usize, usize)> =
        std::collections::HashMap::new();
    for enrollment in &enrollments {
        if let Some(course) = courses.iter().find(|c| c.id == enrollment.course_id) {
            for role in &course.required_for_roles {
                let entry = dept_map.entry(role.clone()).or_insert((0, 0));
                entry.0 += 1;
                if matches!(
                    enrollment.status,
                    TrainingEnrollmentStatus::Completed | TrainingEnrollmentStatus::Passed
                ) {
                    entry.1 += 1;
                }
            }
        }
    }
    let by_department: Vec<DepartmentTrainingSummary> = dept_map
        .into_iter()
        .map(|(role, (total, completed))| {
            let rate = if total > 0 {
                (completed as f64 / total as f64) * 100.0
            } else {
                100.0
            };
            DepartmentTrainingSummary {
                role,
                total_enrollments: total,
                completed,
                completion_rate: rate,
            }
        })
        .collect();

    // By category: per-category course/enrollment/completion counts.
    let by_category: Vec<CategoryTrainingSummary> = courses
        .iter()
        .map(|c| &c.category)
        .collect::<std::collections::HashSet<_>>()
        .into_iter()
        .map(|cat| {
            let cat_courses: Vec<&&TrainingCourse> = courses
                .iter()
                .filter(|c| std::mem::discriminant(&c.category) == std::mem::discriminant(cat))
                .collect();
            let total_cat_courses = cat_courses.len();
            let cat_enrollments: Vec<&&TrainingEnrollment> = enrollments
                .iter()
                .filter(|e| cat_courses.iter().any(|c| c.id == e.course_id))
                .collect();
            let total_cat_enrollments = cat_enrollments.len();
            let completed = cat_enrollments
                .iter()
                .filter(|e| {
                    matches!(
                        e.status,
                        TrainingEnrollmentStatus::Completed | TrainingEnrollmentStatus::Passed
                    )
                })
                .count();
            let rate = if total_cat_enrollments > 0 {
                (completed as f64 / total_cat_enrollments as f64) * 100.0
            } else {
                100.0
            };
            CategoryTrainingSummary {
                category: cat.clone(),
                total_courses: total_cat_courses,
                total_enrollments: total_cat_enrollments,
                completion_rate: rate,
            }
        })
        .collect();

    let dashboard = TrainingDashboard {
        total_courses,
        total_enrollments,
        completion_rate,
        overdue_count,
        by_department,
        by_category,
    };
    Ok(Json(dashboard))
}
