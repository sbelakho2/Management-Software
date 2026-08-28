//! Agent context: SERVER-CREATED and immutable to the model.
//!
//! The critical rule: the model can never specify `tenant_id` or `user_id`
//! in a tool call — those are injected by the server-side tool executor
//! from this context.

use serde::{Deserialize, Serialize};
use uuid::Uuid;

/// Everything the agent may know about the caller and the plant. Built by
/// the server from the authenticated request — never from model input.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AgentContext {
    pub tenant_id: Uuid,
    pub user_id: Uuid,
    pub session_id: Option<Uuid>,

    // Plant context (the "where" of every operational fact).
    pub site_id: Option<Uuid>,
    pub value_stream_id: Option<Uuid>,
    pub work_center_id: Option<Uuid>,
    pub shift_id: Option<Uuid>,

    pub roles: Vec<String>,
    /// The caller's effective permission set (resolved by the
    /// authorization service — the agent can never widen it).
    pub permissions: std::collections::HashSet<String>,

    pub locale: String,
    /// IANA timezone identifier (e.g. "Europe/Paris").
    pub timezone: String,

    pub request_id: Uuid,
    pub conversation_id: Option<Uuid>,
}

impl AgentContext {
    /// Whether the caller may execute the given permission.
    pub fn can(&self, permission: &str) -> bool {
        self.permissions.iter().any(|p| {
            p == "*:*"
                || p == permission
                || (p.ends_with(":*") && permission.starts_with(&p[..p.len() - 1]))
        })
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn context_cannot_be_mutated_by_tools() {
        let ctx = AgentContext {
            tenant_id: Uuid::new_v4(),
            user_id: Uuid::new_v4(),
            session_id: None,
            site_id: None,
            value_stream_id: None,
            work_center_id: None,
            shift_id: None,
            roles: vec!["operator".to_string()],
            permissions: std::collections::HashSet::from(
                ["production:work-order:read".to_string()],
            ),
            locale: "en".to_string(),
            timezone: "UTC".to_string(),
            request_id: Uuid::new_v4(),
            conversation_id: None,
        };
        assert!(ctx.can("production:work-order:read"));
        assert!(!ctx.can("finance:invoice:create"));
    }

    #[test]
    fn wildcard_permissions_grant() {
        let ctx = AgentContext {
            tenant_id: Uuid::new_v4(),
            user_id: Uuid::new_v4(),
            session_id: None,
            site_id: None,
            value_stream_id: None,
            work_center_id: None,
            shift_id: None,
            roles: vec![],
            permissions: std::collections::HashSet::from(["production:*".to_string()]),
            locale: "en".to_string(),
            timezone: "UTC".to_string(),
            request_id: Uuid::new_v4(),
            conversation_id: None,
        };
        assert!(ctx.can("production:report"));
        assert!(!ctx.can("quality:ncr:read"));
    }
}
