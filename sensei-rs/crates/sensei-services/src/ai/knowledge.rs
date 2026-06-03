//! Knowledge Base — CRUD, Search, and A3 Pattern Management.
//!
//! Ported from the [`KnowledgeBase`] class in
//! [`ai_content_drafting.py`](backend/src/sensei/services/ai/ai_content_drafting.py).

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use uuid::Uuid;

// ---------------------------------------------------------------------------
// Enums
// ---------------------------------------------------------------------------

/// Type of knowledge source.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum KnowledgeSourceType {
    BestPractice,
    LessonLearned,
    Standard,
    Training,
    A3Report,
    ExpertKnowledge,
    ExternalReference,
    Procedure,
}

// ---------------------------------------------------------------------------
// Data Models
// ---------------------------------------------------------------------------

/// A source of approved knowledge.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct KnowledgeSource {
    pub id: Uuid,
    pub title: String,
    pub content: String,
    pub source_type: KnowledgeSourceType,
    pub tags: Vec<String>,
    pub is_approved: bool,
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
}

impl KnowledgeSource {
    /// Create a new [`KnowledgeSource`] with the current timestamp.
    pub fn new(
        title: String,
        content: String,
        source_type: KnowledgeSourceType,
        tags: Vec<String>,
    ) -> Self {
        let now = Utc::now();
        Self {
            id: Uuid::new_v4(),
            title,
            content,
            source_type,
            tags,
            is_approved: true,
            created_at: now,
            updated_at: now,
        }
    }
}

/// An A3 pattern stored in the knowledge base.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct A3Pattern {
    pub id: Uuid,
    pub title: String,
    pub problem_pattern: String,
    pub countermeasure: String,
    pub success_rate: f64,
    pub tags: Vec<String>,
    pub created_at: DateTime<Utc>,
}

// ---------------------------------------------------------------------------
// Built-in Knowledge Data
// ---------------------------------------------------------------------------

/// Returns the default knowledge sources seeded into a new knowledge base.
fn default_knowledge_sources() -> Vec<KnowledgeSource> {
    use KnowledgeSourceType::*;

    vec![
        KnowledgeSource::new(
            "5S Methodology".to_string(),
            "Sort (Seiri), Set in Order (Seiton), Shine (Seiso), Standardize (Seiketsu), \
             Sustain (Shitsuke). The foundation of visual workplace organization."
                .to_string(),
            BestPractice,
            vec![
                "5s".to_string(),
                "workplace organization".to_string(),
                "lean".to_string(),
                "visual management".to_string(),
            ],
        ),
        KnowledgeSource::new(
            "SMED - Single Minute Exchange of Die".to_string(),
            "A lean method to reduce setup/changeover time to under 10 minutes. \
             Key steps: separate internal and external setup, convert internal to \
             external, streamline all aspects."
                .to_string(),
            BestPractice,
            vec![
                "smed".to_string(),
                "setup reduction".to_string(),
                "changeover".to_string(),
                "lean".to_string(),
            ],
        ),
        KnowledgeSource::new(
            "Poka-Yoke - Mistake Proofing".to_string(),
            "Design error detection and prevention mechanisms into processes. \
             Types: contact methods, constant value methods, motion-step methods."
                .to_string(),
            BestPractice,
            vec![
                "poka-yoke".to_string(),
                "mistake proofing".to_string(),
                "quality".to_string(),
                "error prevention".to_string(),
            ],
        ),
        KnowledgeSource::new(
            "Standardized Work".to_string(),
            "Documented best practice for each operation. Three elements: \
             takt time, work sequence, and standard WIP. The foundation for \
             continuous improvement (kaizen)."
                .to_string(),
            Standard,
            vec![
                "standardized work".to_string(),
                "standard work".to_string(),
                "takt time".to_string(),
                "work sequence".to_string(),
            ],
        ),
        KnowledgeSource::new(
            "Kaizen - Continuous Improvement".to_string(),
            "Small, incremental improvements involving everyone. PDCA cycle: \
             Plan → Do → Check → Act. Kaizen events focus on specific areas \
             for rapid improvement."
                .to_string(),
            BestPractice,
            vec![
                "kaizen".to_string(),
                "continuous improvement".to_string(),
                "pdca".to_string(),
                "improvement".to_string(),
            ],
        ),
        KnowledgeSource::new(
            "Value Stream Mapping".to_string(),
            "A lean tool to map the flow of materials and information. \
             Identifies value-added vs non-value-added activities. Current \
             state vs future state maps."
                .to_string(),
            BestPractice,
            vec![
                "value stream mapping".to_string(),
                "vsm".to_string(),
                "flow".to_string(),
                "waste identification".to_string(),
            ],
        ),
        KnowledgeSource::new(
            "TPM - Total Productive Maintenance".to_string(),
            "Maximizes equipment effectiveness through autonomous maintenance, \
             planned maintenance, training, and early equipment management. \
             Goal: zero breakdowns, zero defects."
                .to_string(),
            BestPractice,
            vec![
                "tpm".to_string(),
                "total productive maintenance".to_string(),
                "maintenance".to_string(),
                "oee".to_string(),
            ],
        ),
        KnowledgeSource::new(
            "Kanban - Pull System".to_string(),
            "A scheduling system that signals when to produce and move materials. \
             Types: production kanban, withdrawal kanban, signal kanban. \
             Enables just-in-time production."
                .to_string(),
            BestPractice,
            vec![
                "kanban".to_string(),
                "pull system".to_string(),
                "just in time".to_string(),
                "jit".to_string(),
            ],
        ),
        KnowledgeSource::new(
            "A3 Problem Solving".to_string(),
            "A structured problem-solving approach using a single A3-sized sheet. \
             Sections: Problem Statement, Current State, Target State, Root \
             Cause Analysis, Countermeasures, Implementation Plan, Results, \
             Reflection."
                .to_string(),
            A3Report,
            vec![
                "a3".to_string(),
                "problem solving".to_string(),
                "root cause".to_string(),
                "structured thinking".to_string(),
            ],
        ),
        KnowledgeSource::new(
            "Hoshin Kanri - Policy Deployment".to_string(),
            "A strategic planning method that aligns organizational goals with \
             daily operations. Catchball process ensures two-way communication \
             between levels."
                .to_string(),
            BestPractice,
            vec![
                "hoshin kanri".to_string(),
                "policy deployment".to_string(),
                "strategy".to_string(),
                "catchball".to_string(),
            ],
        ),
    ]
}

/// Returns the default A3 patterns.
fn default_a3_patterns() -> Vec<A3Pattern> {
    vec![
        A3Pattern {
            id: Uuid::new_v4(),
            title: "Defect Rate Reduction".to_string(),
            problem_pattern: "High defect rate in production".to_string(),
            countermeasure: "Implement poka-yoke, standardize work, and enhance training"
                .to_string(),
            success_rate: 0.78,
            tags: vec![
                "defects".to_string(),
                "quality".to_string(),
                "training".to_string(),
            ],
            created_at: Utc::now(),
        },
        A3Pattern {
            id: Uuid::new_v4(),
            title: "Setup Time Reduction".to_string(),
            problem_pattern: "Long changeover times".to_string(),
            countermeasure: "Implement SMED methodology with video analysis".to_string(),
            success_rate: 0.85,
            tags: vec![
                "smed".to_string(),
                "setup".to_string(),
                "changeover".to_string(),
            ],
            created_at: Utc::now(),
        },
        A3Pattern {
            id: Uuid::new_v4(),
            title: "Inventory Reduction".to_string(),
            problem_pattern: "Excess WIP and finished goods inventory".to_string(),
            countermeasure: "Implement kanban pull system and reduce batch sizes".to_string(),
            success_rate: 0.72,
            tags: vec![
                "inventory".to_string(),
                "kanban".to_string(),
                "pull system".to_string(),
            ],
            created_at: Utc::now(),
        },
        A3Pattern {
            id: Uuid::new_v4(),
            title: "Downtime Reduction".to_string(),
            problem_pattern: "Frequent equipment breakdowns".to_string(),
            countermeasure: "Implement TPM autonomous maintenance and OEE tracking".to_string(),
            success_rate: 0.81,
            tags: vec![
                "tpm".to_string(),
                "downtime".to_string(),
                "maintenance".to_string(),
                "oee".to_string(),
            ],
            created_at: Utc::now(),
        },
    ]
}

// ---------------------------------------------------------------------------
// KnowledgeBase
// ---------------------------------------------------------------------------

/// A knowledge base of approved sources and A3 patterns.
///
/// Supports CRUD operations, tag-based search, and relevance scoring.
pub struct KnowledgeBase {
    sources: Vec<KnowledgeSource>,
    a3_patterns: Vec<A3Pattern>,
}

impl KnowledgeBase {
    /// Create a new [`KnowledgeBase`] seeded with default knowledge.
    pub fn new() -> Self {
        Self {
            sources: default_knowledge_sources(),
            a3_patterns: default_a3_patterns(),
        }
    }

    /// Create an empty [`KnowledgeBase`] with no seeded data.
    pub fn empty() -> Self {
        Self {
            sources: Vec::new(),
            a3_patterns: Vec::new(),
        }
    }

    // -- Source Management ---------------------------------------------------

    /// List all knowledge sources.
    pub fn list_sources(&self) -> &[KnowledgeSource] {
        &self.sources
    }

    /// Get a single knowledge source by ID.
    pub fn get_source(&self, source_id: Uuid) -> Option<&KnowledgeSource> {
        self.sources.iter().find(|s| s.id == source_id)
    }

    /// Add a new knowledge source.
    pub fn add_source(&mut self, source: KnowledgeSource) {
        self.sources.push(source);
    }

    /// Remove a knowledge source by ID.
    pub fn remove_source(&mut self, source_id: Uuid) -> Option<KnowledgeSource> {
        if let Some(pos) = self.sources.iter().position(|s| s.id == source_id) {
            Some(self.sources.remove(pos))
        } else {
            None
        }
    }

    /// Search sources by query string, using relevance scoring.
    ///
    /// Scoring:
    /// - Title match: +0.5 per match
    /// - Content match: +0.3 per match
    /// - Tag matching: +0.2 per matching tag
    pub fn search_sources(&self, query: &str) -> Vec<&KnowledgeSource> {
        let query_lower = query.to_lowercase();
        let query_terms: Vec<&str> = query_lower
            .split_whitespace()
            .filter(|t| t.len() >= 2)
            .collect();

        if query_terms.is_empty() {
            return Vec::new();
        }

        let mut scored: Vec<(f64, &KnowledgeSource)> = self
            .sources
            .iter()
            .filter_map(|source| {
                let source_title = source.title.to_lowercase();
                let source_content = source.content.to_lowercase();

                let mut score = 0.0f64;

                for term in &query_terms {
                    // Title match (highest weight)
                    if source_title.contains(term) {
                        score += 0.5;
                    }

                    // Content match
                    if source_content.contains(term) {
                        score += 0.3;
                    }

                    // Tag matching
                    for tag in &source.tags {
                        if tag.to_lowercase().contains(term) {
                            score += 0.2;
                        }
                    }
                }

                if score > 0.0 {
                    Some((score, source))
                } else {
                    None
                }
            })
            .collect();

        // Sort by score descending
        scored.sort_by(|a, b| {
            b.0.partial_cmp(&a.0)
                .unwrap_or(std::cmp::Ordering::Equal)
        });

        scored.into_iter().map(|(_, s)| s).collect()
    }

    /// Search sources by tag.
    pub fn search_by_tag(&self, tag: &str) -> Vec<&KnowledgeSource> {
        let tag_lower = tag.to_lowercase();
        self.sources
            .iter()
            .filter(|s| s.tags.iter().any(|t| t.to_lowercase() == tag_lower))
            .collect()
    }

    /// Get only approved sources.
    pub fn get_approved_sources(&self) -> Vec<&KnowledgeSource> {
        self.sources.iter().filter(|s| s.is_approved).collect()
    }

    // -- A3 Pattern Management -----------------------------------------------

    /// Get all A3 patterns.
    pub fn get_a3_patterns(&self) -> &[A3Pattern] {
        &self.a3_patterns
    }

    /// Search A3 patterns by problem pattern or title.
    pub fn search_a3_patterns(&self, query: &str) -> Vec<&A3Pattern> {
        let query_lower = query.to_lowercase();
        let mut scored: Vec<(f64, &A3Pattern)> = self
            .a3_patterns
            .iter()
            .filter_map(|pattern| {
                let mut score = 0.0f64;

                if pattern
                    .title
                    .to_lowercase()
                    .contains(&query_lower)
                {
                    score += 0.5;
                }
                if pattern
                    .problem_pattern
                    .to_lowercase()
                    .contains(&query_lower)
                {
                    score += 0.4;
                }
                for tag in &pattern.tags {
                    if tag.to_lowercase().contains(&query_lower) {
                        score += 0.3;
                    }
                }

                if score > 0.0 {
                    Some((score, pattern))
                } else {
                    None
                }
            })
            .collect();

        scored.sort_by(|a, b| {
            b.0.partial_cmp(&a.0)
                .unwrap_or(std::cmp::Ordering::Equal)
        });

        scored.into_iter().map(|(_, p)| p).collect()
    }

    /// Add a new A3 pattern.
    pub fn add_a3_pattern(&mut self, pattern: A3Pattern) {
        self.a3_patterns.push(pattern);
    }

    // -- Export / Import -----------------------------------------------------

    /// Export the knowledge base state as serializable data.
    pub fn export_state(&self) -> HashMap<String, serde_json::Value> {
        let mut state = HashMap::new();
        state.insert(
            "source_count".to_string(),
            serde_json::Value::Number(serde_json::Number::from(self.sources.len() as u64)),
        );
        state.insert(
            "a3_pattern_count".to_string(),
            serde_json::Value::Number(serde_json::Number::from(self.a3_patterns.len() as u64)),
        );
        state
    }

    /// Get statistics about the knowledge base.
    pub fn get_stats(&self) -> HashMap<String, serde_json::Value> {
        let mut stats = HashMap::new();
        stats.insert(
            "total_sources".to_string(),
            serde_json::Value::Number(serde_json::Number::from(self.sources.len() as u64)),
        );
        stats.insert(
            "approved_sources".to_string(),
            serde_json::Value::Number(serde_json::Number::from(
                self.sources.iter().filter(|s| s.is_approved).count() as u64,
            )),
        );
        stats.insert(
            "total_a3_patterns".to_string(),
            serde_json::Value::Number(serde_json::Number::from(self.a3_patterns.len() as u64)),
        );
        stats
    }
}

impl Default for KnowledgeBase {
    fn default() -> Self {
        Self::new()
    }
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_new_knowledge_base_has_default_sources() {
        let kb = KnowledgeBase::new();
        assert!(!kb.sources.is_empty());
        assert!(!kb.a3_patterns.is_empty());
    }

    #[test]
    fn test_empty_knowledge_base() {
        let kb = KnowledgeBase::empty();
        assert_eq!(kb.list_sources().len(), 0);
        assert_eq!(kb.get_a3_patterns().len(), 0);
    }

    #[test]
    fn test_add_and_get_source() {
        let mut kb = KnowledgeBase::empty();
        let source = KnowledgeSource::new(
            "Test Knowledge".to_string(),
            "Test content".to_string(),
            KnowledgeSourceType::BestPractice,
            vec!["test".to_string()],
        );
        let id = source.id;
        kb.add_source(source);

        assert!(kb.get_source(id).is_some());
        assert_eq!(kb.list_sources().len(), 1);
    }

    #[test]
    fn test_remove_source() {
        let mut kb = KnowledgeBase::empty();
        let source = KnowledgeSource::new(
            "Remove Me".to_string(),
            "Content".to_string(),
            KnowledgeSourceType::LessonLearned,
            vec![],
        );
        let id = source.id;
        kb.add_source(source);
        assert!(kb.remove_source(id).is_some());
        assert!(kb.get_source(id).is_none());
    }

    #[test]
    fn test_search_sources_by_title() {
        let kb = KnowledgeBase::new();
        let results = kb.search_sources("SMED");
        assert!(!results.is_empty());
        assert!(results.iter().any(|s| s.title.contains("SMED")));
    }

    #[test]
    fn test_search_sources_by_content() {
        let kb = KnowledgeBase::new();
        let results = kb.search_sources("mistake proofing");
        assert!(!results.is_empty());
        assert!(results.iter().any(|s| s.content.contains("mistake proofing")));
    }

    #[test]
    fn test_search_sources_by_tag() {
        let kb = KnowledgeBase::new();
        let results = kb.search_by_tag("kaizen");
        assert!(!results.is_empty());
    }

    #[test]
    fn test_search_sources_no_match() {
        let kb = KnowledgeBase::new();
        let results = kb.search_sources("xyznonexistentkeyword");
        assert!(results.is_empty());
    }

    #[test]
    fn test_search_a3_patterns() {
        let kb = KnowledgeBase::new();
        let results = kb.search_a3_patterns("defect");
        assert!(!results.is_empty());
    }

    #[test]
    fn test_add_a3_pattern() {
        let mut kb = KnowledgeBase::empty();
        let pattern = A3Pattern {
            id: Uuid::new_v4(),
            title: "Test Pattern".to_string(),
            problem_pattern: "Test problem".to_string(),
            countermeasure: "Test solution".to_string(),
            success_rate: 0.9,
            tags: vec!["test".to_string()],
            created_at: Utc::now(),
        };
        kb.add_a3_pattern(pattern);
        assert_eq!(kb.get_a3_patterns().len(), 1);
    }

    #[test]
    fn test_scoring_weights() {
        let kb = KnowledgeBase::new();
        // Search for something that should match title strongly
        let results = kb.search_sources("Kanban");
        assert!(!results.is_empty());
        // The top result should have Kanban-related content
        assert!(results[0].title.contains("Kanban"));
    }

    #[test]
    fn test_knowledge_source_constructor() {
        let source = KnowledgeSource::new(
            "Title".to_string(),
            "Content".to_string(),
            KnowledgeSourceType::Training,
            vec!["tag1".to_string(), "tag2".to_string()],
        );
        assert!(source.is_approved);
        assert_eq!(source.tags.len(), 2);
    }
}
